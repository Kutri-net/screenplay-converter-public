"""Format-neutral screenplay model shared by every reader and writer.

A Script has a title page (two text blocks, like Movie Magic: a centered title block and a
contact block) and a flat list of Elements. Each Element has a type and styled text runs.
"""

ACTION = 'action'
SCENE = 'scene'
SHOT = 'shot'
CHARACTER = 'character'
DIALOGUE = 'dialogue'
PAREN = 'parenthetical'
TRANSITION = 'transition'
CENTERED = 'centered'
PAGEBREAK = 'pagebreak'
NOTE = 'note'

TYPES = (ACTION, SCENE, SHOT, CHARACTER, DIALOGUE, PAREN, TRANSITION, CENTERED, PAGEBREAK, NOTE)
STYLES = ('bold', 'italic', 'underline')


class Element:
    __slots__ = ('type', 'runs', 'scene_number', 'dual')

    def __init__(self, type_, runs=None, scene_number=None, dual=False):
        self.type = type_
        self.runs = runs or []          # list of (text, frozenset of STYLES)
        self.scene_number = scene_number
        self.dual = dual

    @classmethod
    def plain(cls, type_, text, **kw):
        return cls(type_, [(text, frozenset())] if text else [], **kw)

    @property
    def text(self):
        return ''.join(t for t, _ in self.runs)

    def __repr__(self):
        return 'Element(%s, %r)' % (self.type, self.text[:40])


class Script:
    def __init__(self, title_block=None, contact_block=None, elements=None):
        self.title_block = title_block or []      # list of lines (centered block)
        self.contact_block = contact_block or []  # list of lines (contact / notes block)
        self.elements = elements or []

    @property
    def has_title_page(self):
        return any(l.strip() for l in self.title_block + self.contact_block)


def merge_runs(runs):
    """Join neighbouring runs with the same style and drop empty ones."""
    out = []
    for text, st in runs:
        if not text:
            continue
        if out and out[-1][1] == st:
            out[-1] = (out[-1][0] + text, st)
        else:
            out.append((text, st))
    return out


def runs_from_events(items):
    """Turn a stream of str and ('style', name, on) tuples into runs."""
    state = set()
    runs = []
    for it in items:
        if isinstance(it, tuple):
            _, name, on = it
            (state.add if on else state.discard)(name)
        else:
            runs.append((it, frozenset(state)))
    return merge_runs(runs)


_CONTROL = dict.fromkeys(i for i in range(32) if i not in (9, 10))


def clean(text):
    """Drop control characters that no output format can hold (XML forbids them)."""
    return text.translate(_CONTROL)


def strip_runs(runs):
    """Clean control characters and trim leading and trailing whitespace across runs."""
    runs = [[clean(t), s] for t, s in merge_runs(runs)]
    runs = [r for r in runs if r[0]]
    while runs and not runs[0][0].lstrip():
        runs.pop(0)
    while runs and not runs[-1][0].rstrip():
        runs.pop()
    if runs:
        runs[0][0] = runs[0][0].lstrip()
        runs[-1][0] = runs[-1][0].rstrip()
    return [(t, s) for t, s in runs if t]


def upper_runs(runs):
    return [(t.upper(), s) for t, s in runs]
