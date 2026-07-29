# Font Production Project Template (For Glyphs)

## Fork notes

This is a personal fork of [colinmford/font-production-project-template-glyphs](https://github.com/colinmford/font-production-project-template-glyphs) — all credit for the original pipeline design goes to Colin Ford. If you're looking for the canonical version of this template, go there instead.

Full disclosure: I'm a type designer, not a build-tooling person, and I largely have no idea what I'm doing under the hood here — this fork happened by messing around with [Claude Code](https://claude.com/claude-code) and seeing what stuck. Use at your own risk, and always sanity-check what a build script does before you run it against real work.

### What's changed from upstream

- Added `C  Project Files/py/prepareGlyphsFile.py`, wired in as the first step of both `static-build.sh` and `vf-build.sh`. Before any font gets built, it:
  - silently fills in studio-identity fields (designer, manufacturer, vendor ID, copyright) from `C  Project Files/py/studioConfig.py` if they're empty in the `.glyphs` file, so they don't need to be retyped for every new project, and
  - aborts the build with a specific list of what's missing if project-specific fields (family name, vertical metric custom parameters) haven't been set yet — those need real judgment in Glyphs.app, so the script deliberately never guesses or prompts for them.
- Added `C  Project Files/py/studioConfig.py` — one place to edit studio-wide defaults instead of hand-entering them per project.

---

Replace this Readme with info about your project!

Note: This template is for Glyphs. GlyphsLib is an unofficial tool to generate Glyphs files outside of GlyphsApp (see [GlyphsLib](https://github.com/googlefonts/glyphsLib)). It might not cover all use cases, so use caution.

## Commands
### Starting a local development environment
Open this project in your terminal and use the following 3 commands:

Use Python3 to start a new virtual environment:
```bash
python3 -m venv .venv
```

... Activate that environment:
```bash
source .venv/bin/activate
```

... Install the requirements of the project in the virtual environment:
```bash
pip install -r requirements.txt
```

... And finally, if any of the below build commands don't work, you might have left the virtual environment. You just need to re-activate it:
```bash
source .venv/bin/activate
```

### Adding an alias (optional)
It might be useful to make a handy "alias" for the top two commands, since you will by typing them all the time.

First, check which "shell" you are using; newer macs use `zsh`, older macs use `bash`. Run this command to check:
```bash
echo $SHELL
```
... if it says `/bin/zsh` then you're using `zsh`; if it says `/bin/bash`, then you're using `bash`.

Then, paste this command to alias the first two commands above to just `venv`. Replace `~/.zshrc` with `~/.bashrc` if you are using `bash`.
```bash
echo 'alias venv="python3 -m venv .venv && source .venv/bin/activate"' >> ~/.zshrc
```
... then restart the terminal.

From now on you only need to type `venv` to start a virtual environment, or activate one if it already exists.

### Building and testing fonts
To build OTFs, TTFs and WOFFs from `.glyphs` files in `A  Font Sources`, use the following command, or drag the file in to your Terminal:
```bash
./static-build.sh
```

To use `fontbakery` to check the OTFs and TTFs in `B  Builds`, use either of these commands:
```bash
./static-checkOTFs.sh
./static-checkTTFs.sh
```
This will generate an HTML output in `D  Proofs`.

### Freezing the development environment
To “Freeze” all the dependencies in the python environment, run this command: 
```bash
pip freeze > requirements-freeze.txt
```
This make a new `requirements-freeze.txt` with the packages pip has installed and their exact version numbers. This will ensure that the next time you initialize your project and run `pip install -r requirements-freeze.txt`, all the dependencies will be exactly the same as they are now.

# License
Uses MIT license. Demo fonts are Mutator Sans, by Erik van Blokland, also licensed under MIT (or BSD?).