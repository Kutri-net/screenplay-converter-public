"""Final Draft XML (.fdx) reader and writer.

The writer follows the structure of Movie Magic's own FDX export (element settings, page layout)
and adds a Final Draft title page. Script notes are not written (Final Draft keeps them outside
the script text); the caller reports how many were left out.
"""
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

from .model import (ACTION, SCENE, SHOT, CHARACTER, DIALOGUE, PAREN, TRANSITION, CENTERED,
                    PAGEBREAK, NOTE, Element, Script, merge_runs, strip_runs)

READ_TYPES = {'Scene Heading': SCENE, 'Action': ACTION, 'Character': CHARACTER, 'Dialogue': DIALOGUE,
              'Parenthetical': PAREN, 'Transition': TRANSITION, 'Shot': SHOT, 'General': ACTION,
              'Cast List': ACTION, 'New Act': CENTERED, 'End of Act': CENTERED}
WRITE_TYPES = {SCENE: 'Scene Heading', ACTION: 'Action', CHARACTER: 'Character', DIALOGUE: 'Dialogue',
               PAREN: 'Parenthetical', TRANSITION: 'Transition', SHOT: 'Shot', CENTERED: 'Action'}

FONT = ('AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" '
        'Font="Courier Final Draft" RevisionID="0" Size="12"')
TITLE_PARA = ('<Paragraph Alignment="%s" FirstIndent="0.00" Leading="Regular" LeftIndent="1.00" '
              'RightIndent="7.50" SpaceBefore="0" Spacing="1" StartsNewPage="No">')

SETTINGS = '''  <HeaderAndFooter FooterFirstPage="Yes" FooterVisible="No" HeaderFirstPage="No" HeaderVisible="Yes" StartingPage="1">
    <Header>
      <Paragraph Alignment="Right" FirstIndent="0.00" Leading="Regular" LeftIndent="1.25" RightIndent="-1.25" SpaceBefore="0" Spacing="1" StartsNewPage="No">
        <DynamicLabel Type="Page #"/>
        <Text {font} Style="">.</Text>
      </Paragraph>
    </Header>
    <Footer>
      <Paragraph Alignment="Right" FirstIndent="0.00" Leading="Regular" LeftIndent="1.25" RightIndent="-1.25" SpaceBefore="0" Spacing="1" StartsNewPage="No">
        <Text {font} Style=""></Text>
      </Paragraph>
    </Footer>
  </HeaderAndFooter>
  <PageLayout BackgroundColor="#FFFFFFFFFFFF" BottomMargin="57" BreakDialogueAndActionAtSentences="Yes" DocumentLeading="Tight" FooterMargin="36" ForegroundColor="#000000000000" HeaderMargin="36" InvisiblesColor="#808080808080" TopMargin="43" UsesSmartQuotes="Yes">
    <AutoCastList AddParentheses="Yes" AutomaticallyGenerate="No" CastListElement="Cast List"/>
  </PageLayout>
'''.format(font=FONT)

ELEMENTS = [  # type, caps, alignment, left, right, space before, paginate as, return key, shortcut
    ('Scene Heading', True, 'Left', '1.50', '7.25', '12', 'Scene Heading', 'Action', 1),
    ('Action', False, 'Left', '1.50', '7.25', '12', 'Action', 'Action', 2),
    ('Character', True, 'Left', '3.70', '7.25', '12', 'Character', 'Dialogue', 3),
    ('Parenthetical', False, 'Left', '3.00', '4.75', '0', 'Parenthetical', 'Dialogue', 4),
    ('Dialogue', False, 'Left', '2.50', '5.85', '0', 'Dialogue', 'Action', 5),
    ('Transition', True, 'Right', '1.50', '7.25', '12', 'Transition', 'Scene Heading', 6),
    ('Shot', True, 'Left', '1.50', '7.25', '12', 'Scene Heading', 'Action', 7),
]


def is_fdx(data):
    head = data[:400].lstrip(b'\xef\xbb\xbf').lstrip()
    return head.startswith(b'<?xml') and b'<FinalDraft' in data[:2000]


# ---------------------------------------------------------------- reading

def _runs(paragraph):
    runs = []
    for t in paragraph.findall('Text'):
        style = (t.get('Style') or '').lower()
        st = frozenset(n for n, key in (('bold', 'bold'), ('italic', 'italic'), ('underline', 'underline')) if key in style)
        runs.append(((t.text or '').replace('\r\n', '\n').replace('\r', '\n'), st))
    return strip_runs(merge_runs(runs))


def read(data, warnings=None):
    root = ET.fromstring(data)
    script = Script()
    tp = root.find('TitlePage/Content')
    if tp is not None:
        for p in tp.findall('Paragraph'):
            text = ''.join(t.text or '' for t in p.findall('Text'))
            target = script.title_block if p.get('Alignment') == 'Center' else script.contact_block
            for line in text.replace('\r', '\n').split('\n'):
                target.append(line)
        for block in (script.title_block, script.contact_block):
            while block and not block[0].strip():
                block.pop(0)
            while block and not block[-1].strip():
                block.pop()
    content = root.find('Content')
    for p in (content.findall('Paragraph') if content is not None else []):
        if p.get('StartsNewPage') == 'Yes' and script.elements:
            script.elements.append(Element(PAGEBREAK))
        etype = READ_TYPES.get(p.get('Type'), ACTION)
        if p.get('Alignment') == 'Center' and etype == ACTION:
            etype = CENTERED
        runs = _runs(p)
        if runs:
            script.elements.append(Element(etype, runs, scene_number=p.get('Number') if etype == SCENE else None))
    return script


# ---------------------------------------------------------------- writing

def _text(runs):
    out = []
    for text, st in runs:
        style = '+'.join(n for n, key in (('Bold', 'bold'), ('Italic', 'italic'), ('Underline', 'underline')) if key in st)
        out.append('<Text %s Style="%s">%s</Text>' % (FONT, style, escape(text)))
    return ''.join(out) or '<Text %s Style=""></Text>' % FONT


def _title_page(script):
    out = ['  <TitlePage>', '    <Content>']

    def para(align, line):
        out.append('      ' + TITLE_PARA % align + '<Text %s Style="">%s</Text></Paragraph>' % (FONT, escape(line)))
    title = list(script.title_block)
    contact = list(script.contact_block)
    for _ in range(18):
        para('Left', '')
    for line in title:
        para('Center', line)
    for _ in range(max(2, 50 - 18 - len(title) - len(contact))):
        para('Left', '')
    for line in contact:
        para('Left', line)
    out += ['    </Content>', '  </TitlePage>']
    return out


def write(script):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="no" ?>',
           '<FinalDraft DocumentType="Script" Template="No" Version="4">', '  <Content>']
    new_page = False
    for el in script.elements:
        if el.type == PAGEBREAK:
            new_page = True
            continue
        if el.type == NOTE or el.type not in WRITE_TYPES:
            continue
        runs = el.runs
        if el.type == PAREN and not el.text.strip().startswith('('):
            runs = [('(', frozenset())] + list(runs) + [(')', frozenset())]
        attrs = ' Type=%s' % quoteattr(WRITE_TYPES[el.type])
        if el.type == SCENE and el.scene_number:
            attrs = ' Number=%s' % quoteattr(el.scene_number) + attrs
        if el.type == CENTERED:
            attrs += ' Alignment="Center"'
        if new_page:
            attrs += ' StartsNewPage="Yes"'
            new_page = False
        out.append('    <Paragraph%s>%s</Paragraph>' % (attrs, _text(merge_runs(runs))))
    out.append('  </Content>')
    if script.has_title_page:
        out += _title_page(script)
    out.append(SETTINGS.rstrip('\n'))
    for name, caps, align, left, right, before, paginate, ret, key in ELEMENTS:
        out += ['  <ElementSettings Type="%s">' % name,
                '    <FontSpec %s Style="%s"/>' % (FONT, 'AllCaps' if caps else ''),
                '    <ParagraphSpec Alignment="%s" FirstIndent="%s" Leading="Regular" LeftIndent="%s" '
                'RightIndent="%s" SpaceBefore="%s" Spacing="1" StartsNewPage="No"/>'
                % (align, '-0.10' if name == 'Parenthetical' else '0.00', left, right, before),
                '    <Behavior PaginateAs="%s" ReturnKey="%s" Shortcut="%d"/>' % (paginate, ret, key),
                '  </ElementSettings>']
    out.append('</FinalDraft>')
    return ('\n'.join(out) + '\n').encode('utf-8')
