#!/usr/bin/env python3
"""Validate the converter against a local archive of real Movie Magic files.

Usage: python3 tests/validate_archive.py ARCHIVE_DIR [--limit N]

For every .mmsw/.BK file:
- round trips through every writer (mmsw, mmx, fdx, fountain) and compares element types and text
- when a same-name .fdx exists, compares the decoded paragraphs with it
Prints only counts and percentages, never manuscript text, so the output is safe to share.
"""
import difflib
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plugin', 'skills', 'screenplay-convert', 'scripts'))

import screenplay_convert as sc  # noqa: E402
from screenplay_convert import fdx, fountain, mmsw, mmx  # noqa: E402
from screenplay_convert.model import PAGEBREAK, NOTE, CENTERED, ACTION, PAREN, SCENE, CHARACTER, TRANSITION, SHOT, DIALOGUE  # noqa: E402

WRITERS = {
    'mmsw': (mmsw.write, mmsw.read),
    'mmx': (mmx.write, mmx.read),
    'fdx': (fdx.write, fdx.read),
    'fountain': (lambda s: fountain.write(s).encode('utf-8'), lambda d, w=None: fountain.read(d.decode('utf-8'))),
}


def norm(text):
    return re.sub(r'\s+', ' ', text).strip()


def key(script, keep_notes=True, fountain_limits=False):
    """Comparable (type, text) list. fountain_limits applies what Fountain cannot express:
    shots are action, dialogue without a cue is action, a cue without dialogue is action,
    and consecutive dialogue paragraphs are one paragraph."""
    els = [e for e in script.elements if e.type != PAGEBREAK and (keep_notes or e.type != NOTE)]
    out = []
    for i, e in enumerate(els):
        t = ACTION if e.type == CENTERED else e.type
        text = norm(e.text)
        if t == PAREN:
            text = text.strip('()')
        if t in (SCENE, CHARACTER, TRANSITION):
            text = text.upper()
        if fountain_limits:
            prev = out[-1][0] if out else None
            nxt = els[i + 1].type if i + 1 < len(els) else None
            if t == SHOT or (t in (DIALOGUE, PAREN) and prev not in (CHARACTER, DIALOGUE, PAREN)) \
                    or (t == CHARACTER and nxt not in (DIALOGUE, PAREN)):
                t = ACTION
            if t == DIALOGUE and prev == DIALOGUE:
                out[-1] = (t, out[-1][1] + ' ' + text)
                continue
        out.append((t, text))
    return out


def ratio(a, b):
    if not a and not b:
        return 1.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(bl.size for bl in sm.get_matching_blocks()) / max(len(a), len(b))


def main():
    root = sys.argv[1]
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    files = sorted(set(glob.glob(os.path.join(root, '**', '*.mmsw'), recursive=True)
                       + glob.glob(os.path.join(root, '**', '*.BK'), recursive=True)
                       + glob.glob(os.path.join(root, '**', '.*.BK'), recursive=True)))
    if limit:
        files = files[:limit]
    stats = {k: [] for k in WRITERS}
    fdx_pairs = []
    worst = {k: (1.0, '') for k in WRITERS}
    errors = 0
    for n, path in enumerate(files):
        try:
            script, fmt = sc.read(path)
        except Exception as e:
            errors += 1
            print('READ ERROR %s: %s' % (os.path.basename(path), e))
            continue
        for name, (write, read) in WRITERS.items():
            try:
                back = read(write(script))
            except Exception as e:
                errors += 1
                print('%s ERROR %s: %s: %s' % (name, os.path.basename(path), type(e).__name__, e))
                continue
            kw = dict(keep_notes=name != 'fdx', fountain_limits=name == 'fountain')
            r = ratio(key(script, **kw), key(back, **kw))
            stats[name].append(r)
            if r < worst[name][0]:
                worst[name] = (r, os.path.basename(path))
        pair = os.path.splitext(path)[0] + '.fdx'
        if path.lower().endswith('.mmsw') and os.path.exists(pair):
            with open(pair, 'rb') as f:
                ref = fdx.read(f.read())
            a = [(t, x.upper()) for t, x in key(script, keep_notes=False)]
            b = [(t, re.sub(r" \(CONT[’']D\)$", '', x.upper())) for t, x in key(ref)]
            fdx_pairs.append((ratio(a, b), os.path.basename(path)))
    print('files: %d, errors: %d' % (len(files), errors))
    for name, rs in stats.items():
        exact = sum(1 for r in rs if r == 1.0)
        print('round trip via %-8s exact %4d/%d, mean %.4f, worst %.4f (%s)'
              % (name, exact, len(rs), sum(rs) / max(1, len(rs)), worst[name][0], worst[name][1]))
    for r, name in sorted(fdx_pairs):
        print('vs same-name FDX: %.4f  %s' % (r, name))


if __name__ == '__main__':
    main()
