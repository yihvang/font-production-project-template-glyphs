"""
Pre-production gate for .glyphs source files. Runs before every build.

Three different behaviors, on purpose:
  - Studio-identity fields (designer, manufacturer, vendorID, copyright...)
    are the same on every project and safe to guess, so they get filled in
    silently from studioConfig.py if empty.
  - Vertical metrics (typoAscender, winDescent, etc.) follow a documented,
    computable formula (see compute_recommended_metrics below), so this
    script creates the custom parameters AND fills in the computed numbers
    when it's confident in them. The one exception is winAscent/winDescent
    when the font has outlier glyphs (see below) - those are left for you
    to fix in Glyphs first, since writing a number derived from a bug would
    be worse than not writing one.
  - Everything else project-specific (family name, license, stem hints)
    requires real judgment this script can't provide. If missing, it aborts
    the build and tells you exactly what to set in Glyphs.app.

    python prepareGlyphsFile.py "A  Font Sources/MyFont.glyphs"

Vertical-metrics rules implemented here, from Colin Ford's font production
class:
  1/3. Every vertical metric param must be explicitly set - never left for
       the font editor to calculate automatically.
  2.   They must be consistent across the whole family (set once, at the
       font level - not overridden per master).
  6/7. hhea must equal the OS/2 Typo metrics exactly, and LineGap must be
       zero.
  8.   OS/2 win ascent/descent must cover the family's actual ink bounding
       box (every master, every exporting glyph) or glyphs will clip.
  9.   The "Use Typo Metrics" flag must be on.
  10.  typoAscender should clear the tallest common accented cap (checked
       opportunistically - only WARNs, and only if such a glyph exists).

A note on how ink bounds are measured: reading a component's raw x/y offset
straight off a GSLayer is not reliable, because Glyphs resolves automatic
component alignment live (in the UI) and again during the real build, but
does not necessarily keep the stored offset in sync with that resolution.
So bounds here are computed by actually building the master UFOs via
glyphsLib (the same step the real build does) and measuring the resolved
glyphs - this matches what Glyphs.app displays and what fontmake ships.
"""

import sys

import defcon
import glyphsLib
from glyphsLib.classes import WEIGHT_CODES
from studioConfig import STUDIO_DEFAULTS

VERTICAL_METRIC_PARAMS = [
    "typoAscender", "typoDescender", "typoLineGap",
    "hheaAscender", "hheaDescender", "hheaLineGap",
    "winAscent", "winDescent",
]

PLACEHOLDER_FAMILY_NAMES = {"", "Untitled", "New Font", "MutatorMathTest"}

STANDARD_WEIGHT_CLASSES = set(range(100, 1001, 100))

# Common tall accented caps, checked in order - first one that actually
# exists in the font is used for the rule-10 sanity check. Abreveacute is the
# tallest common Latin cap (per Google Fonts guidance and arrowtype/vertical-
# metrics); Agrave is the fallback minimum bar. This is the actual clipping
# safeguard - win=actual-bbox does NOT prevent clipping on its own, since
# "Use Typo Metrics" being on means Word clips at typoAscender specifically,
# ignoring win entirely (see arrowtype/vertical-metrics README).
TALL_ACCENTED_CAPS = ["Abreveacute", "Agrave", "Aacute", "Acircumflex", "Adieresis", "Aring", "Atilde"]

# Target line height as a multiple of the UPM (Colin's rule: 20-30% over).
TARGET_LINE_HEIGHT_RATIO = 1.2

OUTLIER_MARGIN = 1.15  # ink this far past ascender/descender gets flagged
MAX_OUTLIERS_REPORTED = 5


def fill_studio_defaults(font):
    filled = []

    if not font.designer:
        font.designer = STUDIO_DEFAULTS["designer"]
        filled.append("designer")
    if not font.designerURL:
        font.designerURL = STUDIO_DEFAULTS["designerURL"]
        filled.append("designerURL")
    if not font.manufacturer:
        font.manufacturer = STUDIO_DEFAULTS["manufacturer"]
        filled.append("manufacturer")
    if not font.manufacturerURL:
        font.manufacturerURL = STUDIO_DEFAULTS["manufacturerURL"]
        filled.append("manufacturerURL")
    if not font.copyright:
        font.copyright = STUDIO_DEFAULTS["copyright"]
        filled.append("copyright")
    if not font.properties.get("vendorID"):
        font.properties["vendorID"] = STUDIO_DEFAULTS["vendorID"]
        filled.append("vendorID")

    return filled


def ensure_nbsp_shares_space(font):
    """
    Maps U+00A0 (no-break space) onto the same glyph as U+0020, instead of
    requiring a second glyph to be drawn and kept in sync by hand. Skipped
    if any glyph already claims U+00A0 - never overrides existing work.
    """
    already_claimed = any(
        g.unicodes and "00A0" in [u.upper() for u in g.unicodes] for g in font.glyphs
    )
    if already_claimed:
        return False

    space = font.glyphs["space"]
    if space is None or not space.export:
        return False

    space.unicodes = space.unicodes + ["00A0"]
    return True


def active_master_ids(font):
    """
    Master IDs referenced by at least one active, exporting instance. Falls
    back to every master if there are no active instances (e.g. a VF-only
    project with no static instances defined yet).

    Vertical metrics need to cover whatever is actually being built - a
    master that's only used by a deactivated instance (a weight not shipping
    in this build) shouldn't gate or inflate win metrics for a build that
    doesn't include it. Once that instance is reactivated, its master comes
    back into scope automatically.
    """
    ids = set()
    for instance in font.instances:
        if instance.active and instance.exports:
            ids.update(instance.instanceInterpolations.keys())
    return ids or {m.id for m in font.masters}


def active_masters(font):
    """The GSFontMaster objects behind active_master_ids(font)."""
    keep_ids = active_master_ids(font)
    return [m for m in font.masters if m.id in keep_ids]


def resolve_glyph_bounds(font):
    """
    Builds the master UFOs (resolving automatic component alignment, same as
    the real build) and returns {(glyph_name, master_name): (left, bottom,
    right, top)} for every exporting glyph with ink, in every master that's
    actually reachable from an active, exporting instance.
    """
    ufos = glyphsLib.to_ufos(font, ufo_module=defcon)
    keep_ids = active_master_ids(font)
    export_names = {g.name for g in font.glyphs if g.export}

    resolved = {}
    for ufo, master in zip(ufos, font.masters):
        if master.id not in keep_ids:
            continue
        for glyph in ufo:
            if glyph.name not in export_names:
                continue
            b = glyph.bounds
            if b is None:
                continue
            resolved[(glyph.name, master.name)] = b
    return resolved


def compute_family_bounds(resolved):
    """Ink bounding box (bottom, top) across every resolved glyph/master, with source."""
    bottom = top = None
    bottom_source = top_source = None
    for (glyph_name, master_name), (_left, btm, _right, tp) in resolved.items():
        if bottom is None or btm < bottom:
            bottom, bottom_source = btm, (glyph_name, master_name)
        if top is None or tp > top:
            top, top_source = tp, (glyph_name, master_name)
    return bottom, top, bottom_source, top_source


def find_outlier_glyphs(resolved, ascender, descender):
    """
    Every resolved glyph/master whose ink reaches further than OUTLIER_MARGIN
    past the ascender or descender - almost always a genuine design issue
    (stray point, wrong glyph, botched interpolation), not intentional.
    Returns the worst offenders first.
    """
    top_limit = ascender * OUTLIER_MARGIN
    bottom_limit = descender * OUTLIER_MARGIN
    outliers = []
    for (glyph_name, master_name), (_left, btm, _right, tp) in resolved.items():
        if tp > top_limit:
            outliers.append((tp - top_limit, glyph_name, master_name, "top", round(tp)))
        if btm < bottom_limit:
            outliers.append((bottom_limit - btm, glyph_name, master_name, "bottom", round(btm)))
    outliers.sort(key=lambda o: -o[0])
    return outliers


def compute_recommended_metrics(font, resolved):
    upm = font.upm
    cap_height = max((m.capHeight for m in active_masters(font)), default=round(upm * 0.7))
    total = round(upm * TARGET_LINE_HEIGHT_RATIO)
    padding = round((total - cap_height) / 2)
    typo_ascender = cap_height + padding
    typo_descender = -padding

    family_bottom, family_top, _, _ = compute_family_bounds(resolved)
    win_ascent = round(family_top) if family_top is not None else typo_ascender
    win_descent = abs(round(family_bottom)) if family_bottom is not None else abs(typo_descender)

    return {
        "typoAscender": typo_ascender,
        "typoDescender": typo_descender,
        "typoLineGap": 0,
        "hheaAscender": typo_ascender,
        "hheaDescender": typo_descender,
        "hheaLineGap": 0,
        "winAscent": win_ascent,
        "winDescent": win_descent,
    }


def fill_vertical_metrics(font, resolved):
    """
    Creates any missing vertical-metric custom parameters and fills in the
    computed value - except winAscent/winDescent, which are only filled if
    there are no outlier glyphs (see find_outlier_glyphs). An existing value
    is never overwritten.
    """
    upm = font.upm
    ascender = max((m.ascender for m in active_masters(font)), default=round(upm * 0.8))
    descender = min((m.descender for m in active_masters(font)), default=-round(upm * 0.2))
    outliers = find_outlier_glyphs(resolved, ascender, descender)

    recommended = compute_recommended_metrics(font, resolved)
    filled = []

    for p in VERTICAL_METRIC_PARAMS:
        if p in ("winAscent", "winDescent") and outliers:
            continue
        if font.customParameters.get(p) is None:
            font.customParameters[p] = recommended[p]
            filled.append(f"{p}={recommended[p]}")

    if not font.customParameters.get("Use Typo Metrics"):
        font.customParameters["Use Typo Metrics"] = 1
        filled.append("Use Typo Metrics=on")

    return filled, outliers


def check_vertical_metrics(font, resolved):
    problems = []

    current = {}
    for p in VERTICAL_METRIC_PARAMS:
        raw = font.customParameters.get(p)
        if raw is None:
            problems.append(
                f"{p} is not set (Font Info > Font > Custom Parameters)."
            )
            continue
        try:
            current[p] = int(raw)
        except (TypeError, ValueError):
            problems.append(f"{p} is set to {raw!r}, which isn't a whole number.")

    if "typoLineGap" in current and current["typoLineGap"] != 0:
        problems.append(f"typoLineGap must be 0, currently {current['typoLineGap']}.")
    if "hheaLineGap" in current and current["hheaLineGap"] != 0:
        problems.append(f"hheaLineGap must be 0, currently {current['hheaLineGap']}.")

    if "hheaAscender" in current and "typoAscender" in current:
        if current["hheaAscender"] != current["typoAscender"]:
            problems.append(
                "hheaAscender must equal typoAscender - currently "
                f"{current['hheaAscender']} vs {current['typoAscender']}."
            )
    if "hheaDescender" in current and "typoDescender" in current:
        if current["hheaDescender"] != current["typoDescender"]:
            problems.append(
                "hheaDescender must equal typoDescender - currently "
                f"{current['hheaDescender']} vs {current['typoDescender']}."
            )

    family_bottom, family_top, _, _ = compute_family_bounds(resolved)
    if "winAscent" in current and family_top is not None and current["winAscent"] < family_top:
        problems.append(
            f"winAscent ({current['winAscent']}) is smaller than the family's "
            f"actual ink ({round(family_top)}) - glyphs will clip. Needs to be "
            f"at least {round(family_top)}."
        )
    if "winDescent" in current and family_bottom is not None and current["winDescent"] < abs(family_bottom):
        problems.append(
            f"winDescent ({current['winDescent']}) is smaller than the family's "
            f"actual ink ({abs(round(family_bottom))}) - glyphs will clip. Needs "
            f"to be at least {abs(round(family_bottom))}."
        )

    if not font.customParameters.get("Use Typo Metrics"):
        problems.append(
            'The "Use Typo Metrics" custom parameter must be on (Font Info > '
            "Font > Custom Parameters > Use Typo Metrics = enabled), otherwise "
            "Windows/Word will ignore your Typo metrics and use Win "
            "ascent/descent for line height instead."
        )

    for master in font.masters:
        overridden = [p for p in VERTICAL_METRIC_PARAMS if master.customParameters.get(p) is not None]
        if overridden:
            problems.append(
                f"Master '{master.name}' has its own value for "
                f"{', '.join(overridden)} - vertical metrics must be set once "
                "at the font level and be the same across the whole family, "
                "not overridden per master."
            )

    return problems


def check_required(font, resolved):
    problems = []

    if font.familyName in PLACEHOLDER_FAMILY_NAMES:
        problems.append(
            f"familyName is {font.familyName!r} - set a real family name "
            "in Font Info > Font."
        )

    problems.extend(check_vertical_metrics(font, resolved))

    return problems


def check_recommended(font, resolved):
    warnings = []

    if not font.properties.get("licenses"):
        warnings.append(
            "No license set (Font Info > Font > licenses). Fine for a beta, "
            "set before any public/final release."
        )

    for master in font.masters:
        if not master.horizontalStems and not master.verticalStems:
            warnings.append(
                f"Master '{master.name}' has no stem hints (Font Info > "
                "Masters > Hints). Needed before enabling psautohint - "
                "fine to skip until closer to release."
            )

    typo_ascender = font.customParameters.get("typoAscender")
    if typo_ascender is not None:
        for name in TALL_ACCENTED_CAPS:
            hits = {k: v for k, v in resolved.items() if k[0] == name}
            if not hits:
                continue
            for (glyph_name, master_name), (_l, _b, _r, top) in hits.items():
                if int(typo_ascender) < top:
                    warnings.append(
                        f"typoAscender ({typo_ascender}) is shorter than "
                        f"'{glyph_name}' ({round(top)}) in master '{master_name}' "
                        "- that glyph may look cramped against the line height. "
                        "Not a hard failure, just worth a look."
                    )
            break  # only the first tall accented cap that exists is relevant

    for instance in font.instances:
        override = instance.customParameters.get("weightClass")
        if override is not None:
            try:
                value = int(override)
            except (TypeError, ValueError):
                continue
        else:
            value = WEIGHT_CODES.get(instance.weight, 400)
        if value not in STANDARD_WEIGHT_CLASSES:
            warnings.append(
                f"Instance '{instance.name}' has usWeightClass {value}, which "
                "isn't one of the standard 100-1000 steps (100 Thin ... 900 "
                "Black). Might be intentional, might be a typo."
            )

    return warnings


def main():
    if len(sys.argv) != 2:
        print("Usage: python prepareGlyphsFile.py <path-to-glyphs-file>")
        sys.exit(1)

    path = sys.argv[1]
    font = glyphsLib.GSFont(path)

    resolved = resolve_glyph_bounds(font)

    filled = fill_studio_defaults(font)
    if ensure_nbsp_shares_space(font):
        filled.append("space unicodes += U+00A0 (nbsp)")
    metrics_filled, outliers = fill_vertical_metrics(font, resolved)
    filled += metrics_filled

    if filled:
        font.save(path)
        print(f"[prepareGlyphsFile] Filled in: {', '.join(filled)}")

    if outliers:
        print(
            f"[prepareGlyphsFile] WARN: winAscent/winDescent were NOT filled in - "
            f"{len(outliers)} glyph layer(s) reach unusually far past the "
            "ascender/descender, so the computed number can't be trusted yet:"
        )
        for _, glyph_name, master_name, edge, value in outliers[:MAX_OUTLIERS_REPORTED]:
            print(f"    '{glyph_name}' in master '{master_name}': {edge} reaches y={value}")
        if len(outliers) > MAX_OUTLIERS_REPORTED:
            print(f"    ...and {len(outliers) - MAX_OUTLIERS_REPORTED} more")

    warnings = check_recommended(font, resolved)
    for w in warnings:
        print(f"[prepareGlyphsFile] WARN: {w}")

    problems = check_required(font, resolved)
    if problems:
        print("[prepareGlyphsFile] Build aborted - fix these in Glyphs first:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print("[prepareGlyphsFile] OK:", path)


if __name__ == "__main__":
    main()
