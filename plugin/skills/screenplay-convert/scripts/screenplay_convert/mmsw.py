"""Movie Magic Screenwriter 6 binary format (.mmsw, .BK): reader and writer.

Reverse-engineered 2026-10-19 from real files and their same-name FDX/RTF/PDF exports
(1,505 binary files; decoded text matched Movie Magic's own FDX exports at 99.2-99.9 %).

File layout
- Header: 28,208 bytes in files made from the default template. No paragraph count, length or
  checksum fields. Title page: block lengths (uint16 LE) at 0x19BC and 0x19DF, block boxes
  (x, y, width, height) just before them, text (cp1252, CRLF) of both blocks back to back at 0x1BA8.
- Body: paragraph records, each a 19-byte header followed by text and a 0x00 terminator.
  Header: left margin, right margin, space before, all caps, 0, 0, element type, 0A 01 0C,
  2 flag bytes, 0x12, 0, 0, K, laid-out line count, 0, 0, then K extra bytes (per-line
  revision data in revised scripts) before the text.
- Trailer: two 0x00 bytes after the last terminator.

Paragraph text
- byte 0xA0-0xFE: ASCII character + 0x80
- byte 0x80-0x9F: style and revision codes (see CTRL), 0x89 = tab
- 0x7F X: one cp1252 character >= 0x80; X is that byte minus 0x80, plus 0x80 again when the
  result is printable (7F E4 = ä, 7F 12 = ’). 7F A7 is a line break inside the paragraph.
- 0x01-0x7E: dictionary tokens (TOKENS); 0x6F is a line break inside the paragraph.
- Character-name paragraphs are plain cp1252.
"""
import os
import re
import string
import struct

from .model import (ACTION, SCENE, SHOT, CHARACTER, DIALOGUE, PAREN, TRANSITION, CENTERED,
                    PAGEBREAK, NOTE, Element, Script, runs_from_events, strip_runs)

MAGIC = b'ScreenwriterWinVer.'
HEADER_SIZE = 28208
TITLE_LEN1, TITLE_LEN2, TITLE_TEXT, TITLE_END = 0x19BC, 0x19DF, 0x1BA8, 0x23A0
BOX1, BOX2 = 0x19B4, 0x19D7

TOKENS = {}
for _i, _c in enumerate(string.ascii_lowercase):
    TOKENS[0x01 + _i] = 'a' + _c
    TOKENS[0x1B + _i] = 'e' + _c
    TOKENS[0x4F + _i] = ' ' + _c
for _i, _c in enumerate(string.ascii_uppercase):
    TOKENS[0x35 + _i] = ' ' + _c
TOKENS.update({0x69: ' th', 0x6A: ' thi', 0x6B: ' you', 0x6C: ' tha', 0x6D: 'an', 0x6E: '. ',
               0x6F: '\n', 0x70: ' the', 0x71: ' he', 0x72: ' and', 0x73: 'it', 0x74: 'and',
               0x75: 'is', 0x76: 'in', 0x77: 'im', 0x78: 'ie', 0x79: 'ic', 0x7B: 'st',
               0x7C: 'to', 0x7D: 'th', 0x7E: 'ing'})

CTRL = {0x02: ('bold', True), 0x03: ('bold', False), 0x19: ('italic', True), 0x1A: ('italic', False),
        0x15: ('underline', True), 0x16: ('underline', False), 0x0E: ('deleted', True),
        0x0F: ('deleted', False), 0x10: ('inserted', True), 0x11: ('inserted', False)}
STYLE_ON = {'bold': 0x82, 'italic': 0x99, 'underline': 0x95}
STYLE_OFF = {'bold': 0x83, 'italic': 0x9A, 'underline': 0x96}

# element type codes (also MMX <EType>)
READ_TYPES = {0: ACTION, 1: SCENE, 2: SHOT, 3: CHARACTER, 4: DIALOGUE, 5: PAREN, 6: TRANSITION,
              7: CENTERED, 8: PAGEBREAK, 9: SCENE, 10: CENTERED, 11: CENTERED, 20: NOTE}

# most common record header per type in real files: (prefix 6 bytes, type, flags 2 bytes), width in characters
WRITE_FORMAT = {
    ACTION: (b'\x0f\x0a\x0a\x00\x00\x00', 0, b'\x00\x00', 60),
    SCENE: (b'\x0f\x0a\x0a\x01\x00\x00', 1, b'\x00\x00', 60),
    SHOT: (b'\x0f\x0a\x0a\x01\x00\x00', 2, b'\x00\x00', 60),
    CHARACTER: (b'\x25\x0a\x0a\x01\x00\x00', 3, b'\x00\x00', 38),
    DIALOGUE: (b'\x19\x18\x00\x00\x00\x00', 4, b'\x00\x00', 36),
    PAREN: (b'\x1e\x23\x00\x00\x00\x00', 5, b'\x00\x00', 20),
    TRANSITION: (b'\x0f\x0a\x0a\x01\x00\x00', 6, b'\x00\x00', 60),
    NOTE: (b'\x0f\x0a\x0a\x00\x00\x00', 20, b'\x00\x02', 60),
}

HDR = re.compile(rb'(..)(....)([\x00-\x1f])\x0a[\x01-\x0f]\x0c(..)(.)\x00\x00(.)(.)\x00\x00', re.S)


def is_mmsw(data):
    return data.startswith(MAGIC)


# ---------------------------------------------------------------- reading

def _decode(b, warnings):
    items = []
    i = 0
    while i < len(b):
        x = b[i]
        if x == 0x7F and i + 1 < len(b):
            ch = bytes([b[i + 1] | 0x80]).decode('cp1252', 'replace')
            items.append({'\xa7': '\n', '\xa0': ' '}.get(ch, ch))
            i += 2
            continue
        if x >= 0xA0:
            items.append(chr(x - 0x80))
        elif x >= 0x80:
            c = x - 0x80
            if c in CTRL:
                items.append(('style',) + CTRL[c])
            elif c == 0x09:
                items.append('    ')
            else:
                warnings.append('unknown control code 0x%02x' % x)
        elif x in TOKENS:
            items.append(TOKENS[x])
        else:
            warnings.append('unknown token 0x%02x' % x)
        i += 1
    # deleted revision text (Movie Magic "compare" documents) is dropped, inserted text kept
    out, deleted = [], False
    for it in items:
        if isinstance(it, tuple) and it[1] in ('deleted', 'inserted'):
            if it[1] == 'deleted':
                deleted = it[2]
            continue
        if not deleted:
            out.append(it)
    return out


def _title_blocks(d):
    l1 = struct.unpack('<H', d[TITLE_LEN1:TITLE_LEN1 + 2])[0]
    l2 = struct.unpack('<H', d[TITLE_LEN2:TITLE_LEN2 + 2])[0]
    raw = d[TITLE_TEXT:TITLE_TEXT + l1 + l2]
    if len(raw) != l1 + l2 or b'\x00' in raw:
        end = d.find(b'\x00', TITLE_TEXT)
        return _lines(d[TITLE_TEXT:end]), []
    return _lines(raw[:l1]), _lines(raw[l1:])


def _lines(b):
    # Windows-written files use CRLF, Mac-written files CR
    return b.decode('cp1252', 'replace').replace('\r\n', '\n').replace('\r', '\n').split('\n')


def read(data, warnings=None):
    warnings = [] if warnings is None else warnings
    version = data[len(MAGIC):len(MAGIC) + 6].strip(b' \x00').decode('ascii', 'replace')
    if not version.startswith('6.'):
        raise ValueError('this is a Movie Magic Screenwriter %s file (usually .scw), which is not supported. '
                         'Open it in Movie Magic 6 and save it as .mmsw, or use an FDX/RTF export of the same version.'
                         % version)
    script = Script()
    first = HDR.search(data)
    if first and first.start() > TITLE_TEXT:
        script.title_block, script.contact_block = _title_blocks(data)
    for m in HDR.finditer(data):
        start = m.end() + m.group(6)[0]          # K extra bytes (per-line revision data) precede the text
        end = data.find(b'\x00', start)
        if end < 0:
            end = len(data)
        code = m.group(3)[0]
        etype = READ_TYPES.get(code)
        if etype is None:
            continue
        raw = data[start:end]
        if etype == PAGEBREAK:
            script.elements.append(Element(PAGEBREAK))
            continue
        if etype == CHARACTER:
            runs = [(raw.replace(b'\x7f', b'').decode('cp1252', 'replace'), frozenset())]
        else:
            runs = runs_from_events(_decode(raw, warnings))
        runs = strip_runs(runs)
        if runs:
            script.elements.append(Element(etype, runs))
    if not script.elements:
        warnings.append('no screenplay paragraphs were found in this Movie Magic file')
    return script


# ---------------------------------------------------------------- writing

def _template():
    path = os.path.join(os.path.dirname(__file__), 'templates', 'mmsw-header.bin')
    with open(path, 'rb') as f:
        data = bytearray(f.read())
    assert len(data) == HEADER_SIZE and data.startswith(MAGIC)
    return data


def _encode_char(ch):
    if ch == '\n':
        return b'\x6f'
    if ch == '\t':
        return b'\x89'
    o = ord(ch)
    if 0x20 <= o <= 0x7E:
        return bytes([o + 0x80])
    try:
        b = ch.encode('cp1252')[0]
    except UnicodeEncodeError:
        return bytes([ord('?') + 0x80])
    if b < 0x80:
        return bytes([b + 0x80]) if b >= 0x20 else b''
    c = b - 0x80
    return bytes([0x7F, c | 0x80 if c >= 0x20 else c])


def _encode_runs(runs):
    out = bytearray()
    active = set()
    for text, st in runs:
        for name in ('underline', 'italic', 'bold'):
            if name in active and name not in st:
                out.append(STYLE_OFF[name])
                active.discard(name)
        for name in ('bold', 'italic', 'underline'):
            if name in st and name not in active:
                out.append(STYLE_ON[name])
                active.add(name)
        for ch in text:
            out += _encode_char(ch)
    for name in ('underline', 'italic', 'bold'):
        if name in active:
            out.append(STYLE_OFF[name])
    return bytes(out)


def _line_count(text, width):
    n = 0
    for line in text.split('\n'):
        n += max(1, -(-len(line) // width))
    return max(1, min(n, 255))


def _set_title(data, title, contact):
    def block(lines):
        text = '\r\n'.join(l.rstrip() for l in lines).strip('\r\n')
        return text.encode('cp1252', 'replace')
    b1, b2 = block(title), block(contact)
    capacity = TITLE_END - TITLE_TEXT - 1
    if len(b1) + len(b2) > capacity:
        b2 = b2[:max(0, capacity - len(b1))]
        b1 = b1[:capacity]
    data[TITLE_TEXT:TITLE_END] = b'\x00' * (TITLE_END - TITLE_TEXT)
    data[TITLE_TEXT:TITLE_TEXT + len(b1) + len(b2)] = b1 + b2
    struct.pack_into('<H', data, TITLE_LEN1, len(b1))
    struct.pack_into('<H', data, TITLE_LEN2, len(b2))
    for box, b, centered in ((BOX1, b1, True), (BOX2, b2, False)):
        lines = b.decode('cp1252').split('\r\n') if b else ['']
        width = max(len(l) for l in lines) * 10 + 2
        height = round(len(lines) * 18.67)
        if centered:
            struct.pack_into('<H', data, box, max(0, 423 - width // 2))
        struct.pack_into('<HH', data, box + 4, width, height)


def write(script):
    data = _template()
    _set_title(data, script.title_block, script.contact_block)
    body = bytearray()
    for el in script.elements:
        etype = {CENTERED: ACTION}.get(el.type, el.type)
        if etype == PAGEBREAK or etype not in WRITE_FORMAT:
            continue
        prefix, code, flags, width = WRITE_FORMAT[etype]
        runs = el.runs
        if etype in (SCENE, TRANSITION, CHARACTER):
            runs = [(t.upper(), s) for t, s in runs]
        if etype == PAREN:
            text = ''.join(t for t, _ in runs).strip()
            if text.startswith('(') and text.endswith(')'):
                runs = strip_runs([(t.replace('(', '', 1) if i == 0 else t, s) for i, (t, s) in enumerate(runs)])
                last_t, last_s = runs[-1]
                runs[-1] = (last_t[:-1] if last_t.endswith(')') else last_t, last_s)
        plain = ''.join(t for t, _ in runs)
        if etype == CHARACTER:
            payload = plain.replace('\n', ' ').encode('cp1252', 'replace').replace(b'\x00', b'')
        else:
            payload = _encode_runs(runs)
        if not payload:
            continue
        body += prefix + bytes([code]) + b'\x0a\x01\x0c' + flags + b'\x12\x00\x00\x00' \
            + bytes([_line_count(plain, width)]) + b'\x00\x00' + payload + b'\x00'
    if not body:
        prefix, code, flags, _ = WRITE_FORMAT[ACTION]
        body += prefix + bytes([code]) + b'\x0a\x01\x0c' + flags + b'\x12\x00\x00\x00\x01\x00\x00' + b'\xa0\x00'
    return bytes(data) + bytes(body) + b'\x00\x00'
