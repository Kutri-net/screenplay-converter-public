#!/usr/bin/env python3
"""Install the screenplay-convert skill for Claude Code and/or Codex.

  python3 install.py            # both Claude Code and Codex
  python3 install.py --claude   # only Claude Code  (~/.claude/skills/)
  python3 install.py --codex    # only Codex        (~/.agents/skills/)
  python3 install.py --uninstall

Copies plugin/skills/screenplay-convert into the user's skill folders. Running it again
updates an earlier installation. Nothing else on the computer is changed.
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'plugin', 'skills', 'screenplay-convert')
NAME = 'screenplay-convert'
TARGETS = {
    'claude': ('Claude Code', os.path.join(os.path.expanduser('~'), '.claude', 'skills')),
    'codex': ('Codex', os.path.join(os.path.expanduser('~'), '.agents', 'skills')),
}


def is_ours(path):
    try:
        with open(os.path.join(path, 'SKILL.md'), encoding='utf-8') as f:
            return 'name: %s' % NAME in f.read(2000)
    except OSError:
        return False


def main():
    p = argparse.ArgumentParser(description='Install the screenplay converter skill.')
    p.add_argument('--claude', action='store_true', help='install for Claude Code only')
    p.add_argument('--codex', action='store_true', help='install for Codex only')
    p.add_argument('--uninstall', action='store_true', help='remove the installed skill')
    args = p.parse_args()
    which = [k for k in ('claude', 'codex') if getattr(args, k)] or ['claude', 'codex']

    if sys.version_info < (3, 8):
        print('Python 3.8 or newer is needed (this is %d.%d).' % sys.version_info[:2])
        return 1
    if not os.path.isfile(os.path.join(SOURCE, 'SKILL.md')):
        print('Cannot find %s - run this from the unzipped screenplay-converter folder.' % SOURCE)
        return 1

    for key in which:
        label, folder = TARGETS[key]
        dest = os.path.join(folder, NAME)
        if os.path.exists(dest) and not is_ours(dest):
            print('%s: %s exists and is not this skill; left untouched.' % (label, dest))
            continue
        if os.path.exists(dest):
            shutil.rmtree(dest)
        if args.uninstall:
            print('%s: removed %s' % (label, dest))
            continue
        os.makedirs(folder, exist_ok=True)
        shutil.copytree(SOURCE, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        print('%s: installed to %s' % (label, dest))
    if not args.uninstall:
        print('Done. Start a new Claude Code or Codex conversation and ask, for example:')
        print('  "Muunna tämä käsikirjoitus Fountainiksi: <file>"  /  "Convert this screenplay to PDF: <file>"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
