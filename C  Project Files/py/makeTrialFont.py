"""
Makes a "trial" copy of an already-built OTF: identical outlines and
features, but with the studioConfig trial suffix appended to the font's
name-table entries and the license/copyright fields replaced with the
trial notice. This is a full, unrestricted font relabeled for trial
distribution - not a cut-down or feature-limited build.

    python makeTrialFont.py <input.otf> <output.otf>
"""

import sys

from fontTools.ttLib import TTFont
from studioConfig import TRIAL_SUFFIX, TRIAL_COPYRIGHT_SUFFIX, TRIAL_LICENSE

FAMILY_NAME_IDS = {1, 4, 16}  # Family, Full Name, Typographic/Preferred Family
POSTSCRIPT_NAME_IDS = {6}  # no spaces allowed
COPYRIGHT_IDS = {0}
LICENSE_IDS = {13}


def main():
    if len(sys.argv) != 3:
        print("Usage: python makeTrialFont.py <input.otf> <output.otf>")
        sys.exit(1)

    in_path, out_path = sys.argv[1], sys.argv[2]
    font = TTFont(in_path)
    name = font["name"]

    for record in name.names:
        current = record.toUnicode()
        if record.nameID in FAMILY_NAME_IDS:
            record.string = f"{current} {TRIAL_SUFFIX}"
        elif record.nameID in POSTSCRIPT_NAME_IDS:
            record.string = f"{current}{TRIAL_SUFFIX.replace(' ', '')}"
        elif record.nameID in COPYRIGHT_IDS:
            record.string = f"{current} {TRIAL_COPYRIGHT_SUFFIX}"
        elif record.nameID in LICENSE_IDS:
            record.string = TRIAL_LICENSE

    # License (nameID 13) may not exist at all yet if the source font never
    # had one set - modifying existing records above won't add it, so make
    # sure a trial build always ships with an explicit license statement.
    has_license = any(r.nameID in LICENSE_IDS for r in name.names)
    if not has_license:
        name.setName(TRIAL_LICENSE, 13, 3, 1, 0x409)  # Windows, English (US)
        name.setName(TRIAL_LICENSE, 13, 1, 0, 0)  # Macintosh, English

    font.save(out_path)
    print(f"[makeTrialFont] {out_path}")


if __name__ == "__main__":
    main()
