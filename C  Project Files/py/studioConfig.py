"""
Studio-wide defaults for new font projects.

Edit this once per studio/foundry. prepareGlyphsFile.py writes these into
any .glyphs file that doesn't already have them set, so identity fields
don't need to be retyped in Font Info for every new project.
"""

STUDIO_DEFAULTS = {
    "designer": "Yihuang Zhou",
    "designerURL": "https://typeangel.xyz",
    "manufacturer": "Type Angel",
    "manufacturerURL": "https://typeangel.xyz",
    "copyright": "Copyright YSFT INC dba Type Angel",
    "vendorID": "ANGL",
}

# Used by makeTrialFont.py to relabel a full, already-built OTF as a trial
# copy - same outlines/features, different name-table metadata only.
TRIAL_SUFFIX = "Unlicensed Trial"  # appended to family/full/typographic names
TRIAL_COPYRIGHT_SUFFIX = "Trial version - not licensed for commercial or production use."

# TODO: fill this in with your actual trial license text before shipping
# any trial build - this placeholder is not real legal language.
TRIAL_LICENSE = "PLACEHOLDER: replace with your actual trial license text."
