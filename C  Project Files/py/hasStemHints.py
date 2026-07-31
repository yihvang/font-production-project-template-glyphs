"""
Checks whether a compiled OTF's CFF Private dict has stem hints set
(StemSnapV/H or StdVW/HW). psautohint errors out hard if none are present,
so static-build.sh uses this to skip hinting gracefully instead of
crashing the whole build when a project hasn't set stems yet in Glyphs.

Exit code 0: stems are set, safe to run psautohint.
Exit code 1: no stems set (or not a CFF-flavored font).

    python hasStemHints.py path/to/font.otf
"""

import sys

from fontTools.ttLib import TTFont

STEM_KEYS = ("StemSnapV", "StemSnapH", "StdVW", "StdHW")


def main():
    if len(sys.argv) != 2:
        print("Usage: python hasStemHints.py <path-to-otf>")
        sys.exit(1)

    path = sys.argv[1]
    font = TTFont(path)

    if "CFF " not in font:
        sys.exit(1)

    private = font["CFF "].cff.topDictIndex[0].Private
    sys.exit(0 if any(k in private.rawDict for k in STEM_KEYS) else 1)


if __name__ == "__main__":
    main()
