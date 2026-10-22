"""Screenplay PDF writer using only the Python standard library.

Uses the PDF standard Courier fonts (no embedding) with WinAnsi encoding, which covers
Finnish and most Western European letters, the en dash and curly quotes. Characters outside
Windows-1252 are printed as '?'; the caller gets a warning.
"""
import zlib

from .model import (ACTION, SCENE, SHOT, CHARACTER, DIALOGUE, PAREN, TRANSITION, CENTERED,
                    PAGEBREAK, NOTE)

INCH = 72.0
CHAR_W = 7.2          # Courier 12 pt advance width
LINE_H = 12.0
PAPER = {'a4': (595.28, 841.89), 'letter': (612.0, 792.0)}
FONTS = {frozenset(): 'F1', frozenset({'bold'}): 'F2', frozenset({'italic'}): 'F3',
         frozenset({'bold', 'italic'}): 'F4'}

# left edge (inches), width (characters), blank lines before, upper case
LAYOUT = {
    SCENE: (1.5, 60, 1, True),
    SHOT: (1.5, 60, 1, True),
    ACTION: (1.5, 60, 1, False),
    CHARACTER: (3.7, 38, 1, True),
    PAREN: (3.1, 25, 0, False),
    DIALOGUE: (2.5, 35, 0, False),
    TRANSITION: (1.5, 60, 1, True),
    CENTERED: (1.5, 60, 1, False),
}


def _wrap(text, width):
    """Return (start, end) index pairs of wrapped lines; '\n' forces a break."""
    ranges = []
    pos = 0
    for hard in text.split('\n'):
        start, n = pos, len(hard)
        i = 0
        while True:
            if n - i <= width:
                ranges.append((start + i, start + n))
                break
            cut = hard.rfind(' ', i, i + width + 1)
            if cut <= i:
                ranges.append((start + i, start + i + width))
                i += width
            else:
                ranges.append((start + i, start + cut))
                i = cut + 1
            while i < n and hard[i] == ' ':
                i += 1
            if i >= n:
                break
        pos += n + 1
    return ranges


def _styled_lines(runs, width, upper=False):
    chars, styles = [], []
    for text, st in runs:
        if upper:
            text = text.upper()
        chars.append(text)
        styles.extend([st] * len(text))
    text = ''.join(chars)
    lines = []
    for a, b in _wrap(text, width):
        segs = []
        for i in range(a, b):
            st = styles[i]
            if segs and segs[-1][1] == st:
                segs[-1][0] += text[i]
            else:
                segs.append([text[i], st])
        lines.append([(t, s) for t, s in segs])
    return lines


class _Line:
    __slots__ = ('x', 'segs', 'align', 'number')

    def __init__(self, x, segs, align='left', number=None):
        self.x = x
        self.segs = segs
        self.align = align
        self.number = number      # scene number printed in both margins


def _blocks(script):
    """Group elements into layout blocks: (kind, lines, before, extra)."""
    blocks = []
    els = [e for e in script.elements if e.type != NOTE]
    i = 0
    while i < len(els):
        el = els[i]
        if el.type == PAGEBREAK:
            blocks.append(('pagebreak', [], 0, None))
            i += 1
            continue
        if el.type == CHARACTER:
            left, width, before, upper = LAYOUT[CHARACTER]
            name = el.text.replace('\n', ' ').strip().upper()
            lines = [_Line(left * INCH, [(name, frozenset())])]
            j = i + 1
            while j < len(els) and els[j].type in (PAREN, DIALOGUE):
                e = els[j]
                l2, w2, _, _ = LAYOUT[e.type]
                runs = e.runs
                if e.type == PAREN and not e.text.strip().startswith('('):
                    runs = [('(', frozenset())] + list(runs) + [(')', frozenset())]
                for k, segs in enumerate(_styled_lines(runs, w2)):
                    x = l2 * INCH + (CHAR_W if e.type == PAREN and k > 0 else 0)
                    lines.append(_Line(x, segs))
                j += 1
            blocks.append(('dialogue', lines, before, name))
            i = j
            continue
        etype = el.type if el.type in LAYOUT else ACTION
        left, width, before, upper = LAYOUT[etype]
        segs_lines = _styled_lines(el.runs, width, upper)
        align = {TRANSITION: 'right', CENTERED: 'center'}.get(etype, 'left')
        lines = [_Line(left * INCH, s, align) for s in segs_lines]
        if etype == SCENE and el.scene_number and lines:
            lines[0].number = el.scene_number
        kind = 'heading' if etype in (SCENE, SHOT) else etype
        blocks.append((kind, lines, before, el.scene_number if etype == SCENE else None))
        i += 1
    return blocks


def _paginate(blocks, per_page):
    pages = [[]]

    def room():
        return per_page - len(pages[-1])

    def new_page():
        if pages[-1]:
            pages.append([])

    def put(lines, before):
        if pages[-1] and before:
            pages[-1].extend([None] * before)
        pages[-1].extend(lines)

    for n, (kind, lines, before, extra) in enumerate(blocks):
        if kind == 'pagebreak':
            new_page()
            continue
        gap = before if pages[-1] else 0
        need = gap + len(lines)
        if kind == 'heading' and n + 1 < len(blocks):
            nk, nl, nb, _ = blocks[n + 1]
            need += nb + min(2, len(nl))
        if need <= room():
            put(lines, before)
            continue
        if kind == 'dialogue' and len(lines) >= 5:
            fit = room() - gap - 1                     # leave a line for (MORE)
            if fit >= 3 and len(lines) - fit >= 2:
                x_char = lines[0].x
                more = _Line(x_char, [('(MORE)', frozenset())])
                put(lines[:fit] + [more], before)
                rest = lines[fit:]
                while True:
                    new_page()
                    cont = _Line(x_char, [(extra + " (CONT'D)", frozenset())])
                    if len(rest) + 1 <= per_page:
                        put([cont] + rest, 0)
                        break
                    put([cont] + rest[:per_page - 2] + [more], 0)
                    rest = rest[per_page - 2:]
                continue
        if kind in (ACTION, CENTERED) and len(lines) >= 4:
            fit = room() - gap
            if fit >= 2 and len(lines) - fit >= 2:
                put(lines[:fit], before)
                new_page()
                rest = lines[fit:]
                while len(rest) > per_page:
                    put(rest[:per_page], 0)
                    new_page()
                    rest = rest[per_page:]
                put(rest, 0)
                continue
        new_page()
        rest = lines
        while len(rest) > per_page:
            put(rest[:per_page], 0)
            new_page()
            rest = rest[per_page:]
        put(rest, 0)
    return [p for p in pages if p] or [[]]


def _pdf_string(text, bad):
    b = bytearray()
    for ch in text:
        try:
            c = ch.encode('cp1252')
        except UnicodeEncodeError:
            bad.add(ch)
            c = b'?'
        if c in (b'\\', b'(', b')'):
            b += b'\\' + c
        else:
            b += c
    return b'(' + bytes(b) + b')'


def _line_ops(line, y, page_w, bad):
    ops = bytearray()
    total = sum(len(t) for t, _ in line.segs)
    if line.align == 'right':
        x = 7.5 * INCH - total * CHAR_W
    elif line.align == 'center':
        x = 1.5 * INCH + (6.0 * INCH - total * CHAR_W) / 2
    else:
        x = line.x
    for text, st in line.segs:
        font = FONTS[frozenset(s for s in st if s in ('bold', 'italic'))]
        ops += b'BT /%s 12 Tf %.2f %.2f Td %s Tj ET\n' % (font.encode(), x, y, _pdf_string(text, bad))
        if 'underline' in st and text.strip():
            ops += b'%.2f %.2f m %.2f %.2f l S\n' % (x, y - 1.5, x + len(text) * CHAR_W, y - 1.5)
        x += len(text) * CHAR_W
    if line.number:
        num = _pdf_string(line.number, bad)
        ops += b'BT /F1 12 Tf %.2f %.2f Td %s Tj ET\n' % (1.5 * INCH - (len(line.number) + 3) * CHAR_W, y, num)
        ops += b'BT /F1 12 Tf %.2f %.2f Td %s Tj ET\n' % (7.5 * INCH + 2 * CHAR_W, y, num)
    return bytes(ops)


def write(script, paper='a4', warnings=None):
    warnings = [] if warnings is None else warnings
    page_w, page_h = PAPER[paper]
    top = page_h - INCH - LINE_H + 3
    per_page = int((page_h - 2 * INCH) // LINE_H)
    bad = set()
    contents = []

    if script.has_title_page:
        ops = bytearray(b'0.5 w\n')
        title = list(script.title_block)
        y = page_h - 3.5 * INCH
        for line in title:
            ops += _line_ops(_Line(0, [(line, frozenset())], 'center'), y, page_w, bad)
            y -= LINE_H
        contact = [l for l in script.contact_block]
        y = INCH + LINE_H * len(contact)
        for line in contact:
            ops += _line_ops(_Line(1.5 * INCH, [(line, frozenset())]), y, page_w, bad)
            y -= LINE_H
        contents.append(bytes(ops))

    pages = _paginate(_blocks(script), per_page)
    for n, page in enumerate(pages, 1):
        ops = bytearray(b'0.5 w\n')
        if n > 1:
            ops += _line_ops(_Line(0, [('%d.' % n, frozenset())], 'right'), page_h - 0.5 * INCH, page_w, bad)
        y = top
        for line in page:
            if line is not None:
                ops += _line_ops(line, y, page_w, bad)
            y -= LINE_H
        contents.append(bytes(ops))

    if bad:
        warnings.append('characters outside the PDF font were printed as "?": ' + ' '.join(sorted(bad)))

    objs = []
    objs.append(b'<< /Type /Catalog /Pages 2 0 R >>')
    n_pages = len(contents)
    first_page = 8        # 1 catalog, 2 pages, 3-6 fonts, 7 info
    kids = ' '.join('%d 0 R' % (first_page + 2 * i) for i in range(n_pages))
    objs.append(('<< /Type /Pages /Kids [%s] /Count %d >>' % (kids, n_pages)).encode())
    for base in ('Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique'):
        objs.append(('<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding /WinAnsiEncoding >>' % base).encode())
    objs.append(b'<< /Producer (screenplay-convert) >>')
    resources = '<< /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R /F4 6 0 R >> >>'
    for i, content in enumerate(contents):
        stream = zlib.compress(content)
        objs.append(('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources %s /Contents %d 0 R >>'
                     % (page_w, page_h, resources, first_page + 2 * i + 1)).encode())
        objs.append(b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(stream) + stream + b'\nendstream')

    out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % i + body + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for off in offsets:
        out += b'%010d 00000 n \n' % off
    out += b'trailer\n<< /Size %d /Root 1 0 R /Info 7 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xref)
    return bytes(out)
