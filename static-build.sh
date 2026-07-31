#!/bin/bash

# Fail fast
set -e

# -----------------------------------------------------------------------
# configure paths

sourcesDir="A  Font Sources"
buildDir="B  Builds"
proofDir="D  Proofs"

otfDir="$buildDir/OTFs"
ttfDir="$buildDir/TTFs"
woffDir="$buildDir/WOFF2s"

# -----------------------------------------------------------------------
# prepare & check sources
# fills in safe studio-identity defaults, aborts if project-specific fields
# (family name, vertical metrics, etc.) are missing - see prepareGlyphsFile.py

echo "Preparing sources..."

find "$sourcesDir" -path '**/*.glyphs' -print0 | while read -d $'\0' glyphsFile
do
    python "C  Project Files/py/prepareGlyphsFile.py" "$glyphsFile"
done

# -----------------------------------------------------------------------
# build OTFs

echo "Building OTFs..."

# removing old files
rm -rf "$otfDir"

# making the otf directory
mkdir -p "$otfDir"

# making the otf files from the glyphs file
find "$sourcesDir" -path '**/*.glyphs' -print0 | while read -d $'\0' glyphsFile
do
    fontmake --glyphs-path "$glyphsFile" --output otf --interpolate --output-dir "$otfDir" --master-dir "{tmp}" --instance-dir "{tmp}" --overlaps-backend pathops --subroutinizer cffsubr --flatten-components
done

# -----------------------------------------------------------------------
# post-processing OTFS 

# this loops through otfs and...
find "$otfDir" -path '*.otf' -print0 | while read -d $'\0' otfFile
do
    # ... removes Mac names
    python "C  Project Files/py/removeMacNames.py" "$otfFile"
    # ... applies autohinting, but only if stem hints are actually set -
    # psautohint errors out hard otherwise. Fine to skip until closer to
    # release (Font Info > Masters > Hints, once outlines are frozen).
    if python "C  Project Files/py/hasStemHints.py" "$otfFile"; then
        psautohint --all "$otfFile"
    else
        echo "  Skipped autohinting for $(basename "$otfFile") - no stem hints set yet."
    fi
done

# -----------------------------------------------------------------------
# build TTFs

echo " "
echo "Building TTFs..."

# removing old files
rm -rf "$ttfDir"

# making the ttf directory
mkdir -p "$ttfDir"

# making the ttfs from the glyphs file
find "$sourcesDir" -path '**/*.glyphs' -print0 | while read -d $'\0' glyphsFile
do
    fontmake --glyphs-path "$glyphsFile" --output ttf --interpolate --output-dir "$ttfDir" --production-names --overlaps-backend pathops --flatten-components -a "--no-info --stem-width-mode=nnn"
done

# -----------------------------------------------------------------------
# post-processing TTFS 

# this loops through ttfs and...
find "$ttfDir" -path '*.ttf' -print0 | while read -d $'\0' ttfFile
do
    # ... makes sure the head table has "Force ppem to integer values" flag set
    python "C  Project Files/py/fixTTHintedFont.py" "$ttfFile"
    # ... removes Mac names
    python "C  Project Files/py/removeMacNames.py" "$ttfFile"
done


# -----------------------------------------------------------------------
# make web fonts

echo " "
echo "Making WOFF2s..."

# removing old files
rm -rf "$woffDir"

# making the woff2 directory
mkdir -p "$woffDir"

# this loops through all the TTFs in the TTF directory and...
find "$ttfDir" -path '*.ttf' -print0 | while read -d $'\0' ttfFile
do
    # Replaces .ttf with .woff2 in the file name
    woff2name=$(basename "${ttfFile/.ttf/.woff2}")
    # ... and compresses them into WOFF2s
    fonttools ttLib.woff2 compress -o "$woffDir/$woff2name" "$ttfFile"
done


# -----------------------------------------------------------------------
# Tests
# The "1>/dev/null 2>&1 || true" stuff is to limit the output in the terminal

echo " "
echo "Running Tests..."

fontbakery check-universal -n --succinct --html "$proofDir/OTFs.html" "$otfDir/*.otf" 1>/dev/null 2>&1 || true
fontbakery check-universal -n --succinct --html "$proofDir/TTFs.html" "$ttfDir/*.ttf" 1>/dev/null 2>&1 || true
