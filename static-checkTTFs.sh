#!/bin/bash

set -e

buildDir="B  Builds"
proofDir="D  Proofs"

ttfDir="$buildDir/TTF"

fontbakery check-universal -n --succinct --html "$proofDir/TTFs.html" "$ttfDir/*.ttf" 1>/dev/null 2>&1
