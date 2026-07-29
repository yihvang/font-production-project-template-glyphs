"""
Pre-production gate for .glyphs source files. Runs before every build.

Two different behaviors, on purpose:
  - Studio-identity fields (designer, manufacturer, vendorID, copyright...)
    are the same on every project and safe to guess, so they get filled in
    silently from studioConfig.py if empty.
  - Project-specific fields (family name, vertical metrics, license, stem
    hints) require real judgment and can't be safely defaulted. If they're
    missing, this script aborts the build and tells you exactly what to set
    in Glyphs.app - it never guesses or prompts for these.

    python prepareGlyphsFile.py "A  Font Sources/MyFont.glyphs"
"""

import sys

import glyphsLib
from studioConfig import STUDIO_DEFAULTS

VERTICAL_METRIC_PARAMS = [
    "typoAscender", "typoDescender", "typoLineGap",
    "winAscent", "winDescent",
    "hheaAscender", "hheaDescender", "hheaLineGap",
]

PLACEHOLDER_FAMILY_NAMES = {"", "Untitled", "New Font", "MutatorMathTest"}


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


def check_required(font):
    problems = []

    if font.familyName in PLACEHOLDER_FAMILY_NAMES:
        problems.append(
            f"familyName is {font.familyName!r} - set a real family name "
            "in Font Info > Font."
        )

    missing_metrics = [
        p for p in VERTICAL_METRIC_PARAMS if not font.customParameters.get(p)
    ]
    if missing_metrics:
        problems.append(
            "Missing vertical metric custom parameters (Font Info > Font > "
            "Custom Parameters): " + ", ".join(missing_metrics)
        )

    return problems


def check_recommended(font):
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

    return warnings


def main():
    if len(sys.argv) != 2:
        print("Usage: python prepareGlyphsFile.py <path-to-glyphs-file>")
        sys.exit(1)

    path = sys.argv[1]
    font = glyphsLib.GSFont(path)

    filled = fill_studio_defaults(font)
    if filled:
        font.save(path)
        print(f"[prepareGlyphsFile] Filled from studio defaults: {', '.join(filled)}")

    warnings = check_recommended(font)
    for w in warnings:
        print(f"[prepareGlyphsFile] WARN: {w}")

    problems = check_required(font)
    if problems:
        print("[prepareGlyphsFile] Build aborted - fix these in Glyphs first:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print("[prepareGlyphsFile] OK:", path)


if __name__ == "__main__":
    main()
