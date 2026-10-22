"""Fountain reader and writer (https://fountain.io/syntax)."""
import re

from .model import (ACTION, SCENE, SHOT, CHARACTER, DIALOGUE, PAREN, TRANSITION, CENTERED,
                    PAGEBREAK, NOTE, Element, Script, merge_runs, strip_runs)

HEADING = re.compile(r'^(INT|EXT|EST|INT\.?/EXT|I/E)[ .]', re.I)
TITLE_KEY = re.compile(r'^(title|credit|author|authors|source|draft date|date|contact|copyright|notes|revision)\s*:(.*)$', re.I)
SCENE_NUMBER = re.compile(r'\s*#([\w.\-]+)#\s*$')
UPPER_LETTERS = re.compile(r'[^\W\d_]')

# private-use sentinels for emphasis parsing
B_ON, B_OFF, I_ON, I_OFF, U_ON, U_OFF, STAR, UNDER = (chr(0xE000 + i) for i in range(8))
CENTER_KEYS = ('title', 'credit', 'author', 'authors', 'source', 'draft date', 'date', 'revision')


# ---------------------------------------------------------------- reading

def _emphasis(text):
    text = text.replace('\\*', STAR).replace('\\_', UNDER)
    text = re.sub(r'\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*', B_ON + I_ON + r'\1' + I_OFF + B_OFF, text)
    text = re.sub(r'\*\*(?=\S)(.+?)(?<=\S)\*\*', B_ON + r'\1' + B_OFF, text)
    text = re.sub(r'\*(?=\S)(.+?)(?<=\S)\*', I_ON + r'\1' + I_OFF, text)
    text = re.sub(r'_(?=\S)(.+?)(?<=\S)_', U_ON + r'\1' + U_OFF, text)
    text = text.replace(STAR, '*').replace(UNDER, '_')
    state = set()
    runs = []
    buf = ''
    toggles = {B_ON: ('bold', True), B_OFF: ('bold', False), I_ON: ('italic', True),
               I_OFF: ('italic', False), U_ON: ('underline', True), U_OFF: ('underline', False)}
    for ch in text:
        if ch in toggles:
            if buf:
                runs.append((buf, frozenset(state)))
                buf = ''
            name, on = toggles[ch]
            (state.add if on else state.discard)(name)
        else:
            buf += ch
    if buf:
        runs.append((buf, frozenset(state)))
    return merge_runs(runs)


def _runs(lines):
    text = '\n'.join(lines)
    text = re.sub(r'\[\[.*?\]\]', '', text, flags=re.S)   # inline notes are not script text
    return strip_runs(_emphasis(text))


def _is_character(line):
    if line.startswith('@'):
        return True
    name = re.sub(r'\(.*?\)', '', line).rstrip('^').strip()
    return bool(name) and name == name.upper() and bool(UPPER_LETTERS.search(name)) \
        and not HEADING.match(line) and not line.rstrip().endswith('TO:')


def _title_page(lines):
    fields = []
    for line in lines:
        m = TITLE_KEY.match(line)
        if m:
            fields.append([m.group(1).lower(), []])
            if m.group(2).strip():
                fields[-1][1].append(m.group(2).strip())
        elif fields and line.strip():
            fields[-1][1].append(line.strip())
    title, contact = [], []
    for key, values in fields:
        target = title if key in CENTER_KEYS else contact
        if target is title and title:
            title.append('')
        target.extend(_strip_emphasis(v) for v in values)
    return title, contact


def _strip_emphasis(s):
    return ''.join(t for t, _ in _emphasis(s))


def read(text):
    text = text.lstrip('﻿').replace('\r\n', '\n').replace('\r', '\n').expandtabs(4)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)       # boneyard
    lines = text.split('\n')
    script = Script()
    if lines and TITLE_KEY.match(lines[0]):
        end = next((i for i, l in enumerate(lines) if not l.strip()), len(lines))
        script.title_block, script.contact_block = _title_page(lines[:end])
        lines = lines[end:]
    # blocks separated by empty lines; a line of exactly two spaces stays inside a block
    blocks, cur = [], []
    for line in lines:
        if line.strip() or line == '  ':
            cur.append(line.rstrip() if line != '  ' else '')
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    els = script.elements
    for block in blocks:
        first = block[0].strip()
        if re.fullmatch(r'={3,}', first):
            els.append(Element(PAGEBREAK))
            block = block[1:]
            if not block:
                continue
            first = block[0].strip()
        if first.startswith('#') or (first.startswith('=') and not first.startswith('==')):
            continue                                   # sections and synopses are not printed
        if first.startswith('[[') and '\n'.join(block).rstrip().endswith(']]'):
            note = '\n'.join(block).strip()[2:-2].strip()
            els.append(Element.plain(NOTE, note))
            continue
        if first.startswith('!'):
            els.append(Element(ACTION, _runs([block[0].lstrip()[1:]] + block[1:])))
            continue
        if (first.startswith('.') and not first.startswith('..')) or HEADING.match(first):
            heading = first[1:] if first.startswith('.') and not HEADING.match(first) else first
            num = SCENE_NUMBER.search(heading)
            if num:
                heading = heading[:num.start()]
            els.append(Element.plain(SCENE, heading.strip(), scene_number=num.group(1) if num else None))
            if len(block) > 1:
                els.append(Element(ACTION, _runs(block[1:])))
            continue
        if first.startswith('>') and first.endswith('<'):
            els.append(Element(CENTERED, _runs([l.strip().lstrip('>').rstrip('<').strip() for l in block])))
            continue
        if first.startswith('>') or (len(block) == 1 and first == first.upper() and first.endswith('TO:')):
            els.append(Element(TRANSITION, _runs([first.lstrip('>').strip()])))
            continue
        if first.startswith('~'):
            els.append(Element(ACTION, [(t, s | {'italic'}) for t, s in _runs([l.lstrip('~').strip() for l in block])]))
            continue
        if len(block) > 1 and _is_character(first):
            name = first[1:] if first.startswith('@') else first
            dual = name.endswith('^')
            els.append(Element.plain(CHARACTER, name.rstrip('^').strip(), dual=dual))
            dialogue = []
            for line in block[1:]:
                s = line.strip()
                if s.startswith('(') and s.endswith(')'):
                    if dialogue:
                        els.append(Element(DIALOGUE, _runs(dialogue)))
                        dialogue = []
                    els.append(Element(PAREN, _runs([s])))
                else:
                    dialogue.append(s)
            if dialogue:
                els.append(Element(DIALOGUE, _runs(dialogue)))
            continue
        els.append(Element(ACTION, _runs(block)))
    script.elements = [e for e in els if e.runs or e.type == PAGEBREAK]
    return script


# ---------------------------------------------------------------- writing

def _escape(text):
    return text.replace('\\', '\\\\').replace('*', '\\*').replace('_', '\\_')


def render_runs(runs, markup=True):
    out = ''
    for text, st in runs:
        text = _escape(text) if markup else text
        if not st or not markup:
            out += text
            continue
        parts = text.split('\n')
        rendered = []
        for part in parts:
            lead, core, trail = re.match(r'(\s*)(.*?)(\s*)$', part, re.S).groups()
            if core:
                o = ('**' if 'bold' in st else '') + ('*' if 'italic' in st else '') + ('_' if 'underline' in st else '')
                c = ('_' if 'underline' in st else '') + ('*' if 'italic' in st else '') + ('**' if 'bold' in st else '')
                core = o + core + c
            rendered.append(lead + core + trail)
        out += '\n'.join(rendered)
    return out


def _lines(text):
    lines = [l.rstrip() for l in text.strip('\n').split('\n')]
    return '\n'.join(l if l else '  ' for l in lines)


def write(script):
    out = []
    if script.has_title_page:
        title = [l for l in script.title_block if l.strip()]
        if title:
            out.append('Title:')
            out += ['    ' + l for l in title]
        contact = [l for l in script.contact_block if l.strip()]
        if contact:
            out.append('Contact:')
            out += ['    ' + l for l in contact]
        out.append('')
    prev = None
    elements = script.elements
    for i, el in enumerate(elements):
        t = el.type
        nxt = elements[i + 1].type if i + 1 < len(elements) else None
        if t == PAGEBREAK:
            out += ['===', '']
            prev = t
            continue
        text = _lines(render_runs(el.runs, markup=t not in (CHARACTER, NOTE, SCENE)))
        if not text.strip():
            continue
        if t in (DIALOGUE, PAREN) and prev in (CHARACTER, DIALOGUE, PAREN):
            if out and out[-1] == '':
                out.pop()
            if t == PAREN and not text.startswith('('):
                text = '(' + text + ')'
            out += [text, '']
            prev = t
            continue
        if t == SCENE:
            line = text.replace('\n', ' ').upper()
            if not HEADING.match(line):
                line = '.' + line
            if el.scene_number:
                line += ' #%s#' % el.scene_number
            out += [line, '']
        elif t == CHARACTER:
            name = text.replace('\n', ' ').strip().upper()
            if not _is_character(name):
                name = '@' + name
            if out and out[-1] != '':
                out.append('')
            out.append(name + (' ^' if el.dual else ''))
            if nxt not in (DIALOGUE, PAREN):
                out.append('')            # a cue without dialogue is read back as action
        elif t == TRANSITION:
            line = text.replace('\n', ' ').upper()
            out += [line if line.endswith('TO:') else '> ' + line, '']
        elif t == CENTERED:
            out += ['\n'.join('> ' + l.strip() + ' <' for l in text.split('\n')), '']
        elif t == NOTE:
            out += ['[[' + text + ']]', '']
        else:
            # action and shot: force action when Fountain would read the text as something else
            first = text.split('\n')[0]
            plain_first = el.text.split('\n')[0]
            if ('\n' in el.text and UPPER_LETTERS.search(plain_first) and plain_first == plain_first.upper()) \
                    or HEADING.match(first) \
                    or first[:1] in '.!@~>=#[' or first.rstrip().endswith('TO:'):
                text = '!' + text
            out += [text, '']
        # dialogue without a character cue was written as action above
        prev = ACTION if t in (DIALOGUE, PAREN) else t
    return '\n'.join(out).rstrip() + '\n'
