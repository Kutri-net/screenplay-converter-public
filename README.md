# Screenplay converter

*Suomeksi: [README.fi.md](README.fi.md)*

Convert screenplays between Movie Magic Screenwriter, Fountain, Final Draft and PDF on your own computer – without Movie Magic or Final Draft. You ask Claude Code or Codex in VS Code to do it, or run one command yourself.

| From | To |
| --- | --- |
| Movie Magic `.mmsw`, `.BK` backups, `.mmx` | Fountain `.fountain` |
| Final Draft `.fdx` | Final Draft `.fdx` |
| Fountain `.fountain` | PDF `.pdf` (A4 or US Letter) |
| | Movie Magic `.mmsw` / `.mmx` (new, see below) |

Everything runs locally. Your screenplay is not uploaded anywhere.

## What you need

- VS Code with the Claude Code extension or the Codex extension.
- Python 3.8 or newer. Check in the VS Code terminal: `python3 --version` (Windows: `py -3 --version`).
  - Mac: if Python is missing, run `xcode-select --install`.
  - Windows: install from [python.org](https://www.python.org/downloads/) and tick "Add python.exe to PATH".

No other installs are needed.

## Install

1. Download the code: on [github.com/Kutri-net/screenplay-converter-public](https://github.com/Kutri-net/screenplay-converter-public) choose **Code → Download ZIP** and unzip it. Or ask Claude Code or Codex: "Download https://github.com/Kutri-net/screenplay-converter-public and install the screenplay converter from it."
2. Open the unzipped folder in VS Code, or in the Claude or ChatGPT desktop app.
3. Ask Claude Code or Codex: "Run install.py in this folder". Or run it yourself in the terminal: `python3 install.py` (Windows: `py -3 install.py`).
4. Start a new Claude Code or Codex conversation.

`install.py` copies the skill to `~/.claude/skills/` (Claude Code) and `~/.agents/skills/` (Codex). Use `--claude` or `--codex` to install for one of them only, and `--uninstall` to remove it. Running it again updates an earlier installation.

Claude Code command-line users can also install it as a plugin: `/plugin marketplace add Kutri-net/screenplay-converter-public` and `/plugin install screenplay-converter@kutri-screenplay`.

## Use

Ask in your own words, for example:

- "Convert `episode1.mmsw` to Fountain."
- "Make a PDF of this screenplay." (A4; say "US Letter" if you need that)
- "Convert all Movie Magic files in this folder to Final Draft."
- "Turn `draft.fountain` into a Movie Magic file."
- "What is in this .BK file?"

The converter never overwrites an existing file or the original.

### From the command line

```
python3 scripts/convert.py episode1.mmsw episode1.fountain
python3 scripts/convert.py episode1.fountain episode1.pdf --paper letter
python3 scripts/convert.py *.mmsw --to fdx --out-dir converted
python3 scripts/convert.py episode1.BK --info
```

`scripts/convert.py` is inside the installed skill folder (`~/.claude/skills/screenplay-convert/` or `~/.agents/skills/screenplay-convert/`).

## Good to know

- **Movie Magic output is new.** Reading Movie Magic files was tested on over 1,500 real files and matched Movie Magic's own Final Draft exports at 99.6–100 %. Writing `.mmsw` passes the same round-trip tests but has not yet been confirmed in Movie Magic itself. Open the file in Movie Magic once before relying on it. `.mmsw` is for Windows and Mac Movie Magic, `.mmx` for the Mac version only.
- Movie Magic adds scene numbers, (MORE) and (CONT'D) only when printing, so they are not in its files. The PDF adds its own (MORE) and (CONT'D).
- Fountain cannot hold everything: a character name without dialogue becomes an action line, and a shot becomes action.
- Script notes stay in Fountain and Movie Magic files and are left out of PDF and Final Draft.
- Centered text, page breaks and dual dialogue are kept in Fountain and Final Draft, not in Movie Magic files.
- Older Screenwriter 4.x files (`.scw`) are not supported yet. Open them in Movie Magic 6 and save as `.mmsw`, or use a Final Draft or RTF export.
- The PDF uses the standard Courier font. It covers Western European letters (ä, ö, å, é …), dashes and curly quotes; other letters print as `?`, and you get a warning.

## For developers

- `plugin/skills/screenplay-convert/` – the skill: `SKILL.md`, `scripts/convert.py` and the `screenplay_convert` package (Python standard library only)
- `tests/` – `python3 -m unittest discover tests`; `tests/validate_archive.py ARCHIVE_DIR` checks a local archive of real Movie Magic files and prints only counts
- `scripts/build-zip.sh` – builds the download zip into `dist/`
- `mms-testi/` – test files and instructions for checking the Movie Magic output in Movie Magic and Final Draft

The Movie Magic format was worked out by comparing real files with their FDX, RTF and PDF exports; the format notes are at the top of `screenplay_convert/mmsw.py`.

Made by Katri Manninen, [kutri.net](https://kutri.net). MIT License, see [LICENSE](LICENSE).
