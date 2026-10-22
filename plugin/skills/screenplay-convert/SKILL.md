---
name: screenplay-convert
description: Convert screenplays between Movie Magic Screenwriter (.mmsw, .BK backups, .mmx), Fountain (.fountain), Final Draft (.fdx) and PDF on the user's own computer, without Movie Magic or Final Draft installed. Use when the user asks to open, read, convert or export a Movie Magic or Final Draft script, make a PDF of a screenplay, or turn Fountain into Movie Magic or Final Draft. Triggers include "muunna käsikirjoitus", "avaa mmsw", "mmsw fountainiksi", "tee käsikirjoituksesta pdf", "muunna final draftiksi", "fountain movie magiciksi", "convert screenplay", "mmsw to fountain", "fdx to pdf". Not for writing or editing the story itself.
---

# Screenplay converter

Converts screenplays locally with one Python script and the Python standard library. Nothing is uploaded anywhere. Answer the user in the language they write in.

| From | To |
| --- | --- |
| `.mmsw`, `.BK` (Movie Magic 6), `.mmx` (Movie Magic Mac), `.fdx`, `.fountain` | `.fountain`, `.fdx`, `.pdf`, `.mmsw`, `.mmx` |

## Steps

1. Find Python 3.8 or newer: run `python3 --version` (on Windows `py -3 --version`). If it is missing, tell the user to install it from python.org (Windows: tick "Add python.exe to PATH") or, on a Mac, to run `xcode-select --install`, and stop until it works.
2. Locate the converter: `scripts/convert.py` in the folder that contains this SKILL.md. Use its absolute path; quote paths, because screenplay folders often contain spaces and letters such as ä and ö.
3. Confirm the input file exists. If the user named a folder or several files, use batch mode.
4. Choose the output path: same folder and name as the input with the new extension, unless the user gave one. The script never overwrites an existing file or the input; add `--force` only when the user explicitly asks to replace an existing output.
5. Run one of:
   - `python3 "<skill>/scripts/convert.py" "INPUT" "OUTPUT"`
   - `python3 "<skill>/scripts/convert.py" FILES... --to fountain|fdx|pdf|mmsw|mmx --out-dir "FOLDER"`
   - `python3 "<skill>/scripts/convert.py" "INPUT" --info` to describe a file (format, scenes, characters) without converting
   - PDF paper size: A4 by default, `--paper letter` for US Letter
6. Report: the output path, the counts the script printed, and every `warning:` line in plain words. If the script failed, show the error and what to try next.

## What to tell the user

- `.mmsw` output: the Movie Magic writer was reverse-engineered and is new. Ask the user to open the file in Movie Magic once and check it before relying on it. `.mmsw` works in Windows and Mac Movie Magic; `.mmx` only in the Mac version.
- Movie Magic does not store scene numbers, (MORE) or (CONT'D) in the file; it adds them when printing. They are therefore missing from Fountain and FDX made from `.mmsw`, and the PDF adds its own (MORE)/(CONT'D).
- Fountain cannot hold everything: a character cue without dialogue becomes an action line, a shot becomes action, and consecutive dialogue paragraphs of one speaker become one paragraph with line breaks.
- Script notes are kept in Fountain (`[[ ]]`), `.mmsw` and `.mmx`, and left out of PDF and FDX; the script says how many.
- Centered text, page breaks and dual dialogue survive in Fountain and FDX but not in Movie Magic files.
- The PDF uses the built-in Courier font. Letters outside Western European (Windows-1252) are printed as `?`, and the script warns when that happens.
- Movie Magic "compare" documents: deleted revision text is dropped, inserted text is kept.
- Older Screenwriter 4.x files (`.scw`) are not supported; the script stops with a message. Suggest opening the file in Movie Magic 6 and saving it as `.mmsw`, or using an FDX/RTF export of the same version.

## Rules

- Never upload screenplay files or paste their text into web searches or online converters; the work is unpublished.
- Never edit, rename or move the original file.
- Do not change the story text. Formatting differences between programs are reported, not "fixed" by hand.
