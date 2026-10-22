"""Movie Magic Screenwriter Mac XML format (.mmx; Mac 6.5 also saves it under the .mmsw name).

zlib-compressed XML: <MovieMagicScreenwriter><DocumentHeader/><Content><Paragraph/>...</Content>.
The writer uses a header taken from a real Movie Magic 6.5 file with the title page and draft
date emptied (templates/mmx-header.xml). The Windows version of Movie Magic cannot read this format.
"""
import os
import random
import zlib
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from .model import (ACTION, SCENE, SHOT, CHARACTER, DIALOGUE, PAREN, TRANSITION, CENTERED,
                    PAGEBREAK, NOTE, Element, Script, runs_from_events, strip_runs)

READ_TYPES = {'Action': ACTION, 'Scene Heading': SCENE, 'Shot': SHOT, 'Character': CHARACTER,
              'Dialogue': DIALOGUE, 'Parenthetical': PAREN, 'Transition': TRANSITION,
              'Title': CENTERED, 'Act Info': CENTERED, 'Scene Info': CENTERED,
              'Script Note': NOTE, 'Outline': NOTE, 'Page Break': PAGEBREAK}
TAGS = {'BoldOn': ('bold', True), 'BoldOff': ('bold', False), 'ItalOn': ('italic', True),
        'ItalOff': ('italic', False), 'UndOn': ('underline', True), 'UndOff': ('underline', False)}

# Type name, style element in DocumentStyles, characters per line
WRITE_TYPES = {ACTION: ('Action', 'ActionStyle', 63), SCENE: ('Scene Heading', 'SceneStyle', 63),
               SHOT: ('Shot', 'ShotStyle', 63), CHARACTER: ('Character', 'CharNameStyle', 40),
               DIALOGUE: ('Dialogue', 'DialogueStyle', 38), PAREN: ('Parenthetical', 'ParenthStyle', 28),
               TRANSITION: ('Transition', 'TransitionStyle', 19), CENTERED: ('Action', 'ActionStyle', 63),
               NOTE: ('Script Note', 'NoteStyle', 63)}


def is_mmx(data):
    if data[:2] in (b'x\x9c', b'x\xda', b'x\x01', b'x^'):
        try:
            return zlib.decompressobj().decompress(data[:256]).lstrip().startswith(b'<?xml')
        except zlib.error:
            return False
    return data.lstrip()[:200].find(b'<MovieMagicScreenwriter') >= 0


def _xml(data):
    if data[:1] == b'x':
        try:
            return zlib.decompress(data)
        except zlib.error:
            pass
    return data


# ---------------------------------------------------------------- reading

def read(data, warnings=None):
    root = ET.fromstring(_xml(data))
    script = Script()
    records = root.findall('./DocumentHeader/TitlePageInfo/TitlePageRecord')
    blocks = [(r.findtext('Text') or '').replace('\r\n', '\n').replace('\r', '\n').split('\n') for r in records]
    if blocks:
        script.title_block = blocks[0]
        script.contact_block = [l for b in blocks[1:] for l in b]
    for p in root.iter('Paragraph'):
        name = p.findtext('Type')
        etype = READ_TYPES.get(name, ACTION)
        if etype == PAGEBREAK:
            if 'DYNAMIC' not in (p.findtext('PageBreakType') or ''):
                script.elements.append(Element(PAGEBREAK))
            continue
        items = []
        et = p.find('ElementText')
        if et is not None:
            for child in et:
                if child.tag == 'Text':
                    items.append((child.text or '').replace('\r\n', '\n').replace('\r', '\n'))
                elif child.tag in TAGS:
                    items.append(('style',) + TAGS[child.tag])
        runs = strip_runs(runs_from_events(items))
        if runs:
            script.elements.append(Element(etype, runs))
    return script


# ---------------------------------------------------------------- writing

def _header():
    path = os.path.join(os.path.dirname(__file__), 'templates', 'mmx-header.xml')
    with open(path, encoding='utf-8') as f:
        return ET.fromstring(f.read())


def _text_xml(runs):
    out = []
    active = set()
    on = {'bold': '<BoldOn/>', 'italic': '<ItalOn/>', 'underline': '<UndOn/>'}
    off = {'bold': '<BoldOff/>', 'italic': '<ItalOff/>', 'underline': '<UndOff/>'}
    for text, st in runs:
        for name in ('underline', 'italic', 'bold'):
            if name in active and name not in st:
                out.append(off[name])
                active.discard(name)
        for name in ('bold', 'italic', 'underline'):
            if name in st and name not in active:
                out.append(on[name])
                active.add(name)
        out.append('<Text>%s</Text>' % escape(text.replace('\n', '\r')))
    for name in ('underline', 'italic', 'bold'):
        if name in active:
            out.append(off[name])
    return ''.join(out)


def _lines(text, width):
    return max(1, sum(max(1, -(-len(l) // width)) for l in text.split('\n')))


def write(script):
    header = _header()
    records = header.findall('./TitlePageInfo/TitlePageRecord')
    for rec, lines in zip(records, (script.title_block, script.contact_block)):
        rec.find('Text').text = '\r'.join(l.rstrip() for l in lines).strip('\r')
    styles = header.find('./ScriptStyles/DocumentStyles')
    rng = random.Random(len(script.elements))
    paragraphs = []
    for el in script.elements:
        if el.type == PAGEBREAK or el.type not in WRITE_TYPES:
            continue
        name, style_tag, width = WRITE_TYPES[el.type]
        runs = el.runs
        if el.type == PAREN:
            text = el.text.strip()
            if text.startswith('(') and text.endswith(')'):
                runs = [(t, s) for t, s in runs]
                runs[0] = (runs[0][0].lstrip()[1:], runs[0][1])
                runs[-1] = (runs[-1][0].rstrip()[:-1], runs[-1][1])
                runs = strip_runs(runs)
        if not runs:
            continue
        style = ET.tostring(styles.find(style_tag), encoding='unicode')
        style = style.replace('<%s>' % style_tag, '<Style>').replace('</%s>' % style_tag, '</Style>')
        flag = 'IsVis' if el.type == NOTE else 'None'
        paragraphs.append(
            '<Paragraph><Type>%s</Type><UniqueID>%d</UniqueID><SplitID>0</SplitID>'
            '<ElementText>%s</ElementText>%s<Ext>None</Ext><Keep>BreakOK</Keep><RawK>0</RawK>'
            '<NmRev>0</NmRev><Lines>%d</Lines><OutSty>0</OutSty><OutSNm></OutSNm>'
            '<EFlags><Flag>%s</Flag></EFlags></Paragraph>'
            % (name, rng.getrandbits(63), _text_xml(runs), style, _lines(el.text, width), flag))
    header.find('./MiscHeaderFields/TotalElementCount').text = str(len(paragraphs))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<MovieMagicScreenwriter>'
           + ET.tostring(header, encoding='unicode', short_empty_elements=False) + '<Content>' + ''.join(paragraphs)
           + '</Content></MovieMagicScreenwriter>')
    return zlib.compress(xml.encode('utf-8'), 9)
