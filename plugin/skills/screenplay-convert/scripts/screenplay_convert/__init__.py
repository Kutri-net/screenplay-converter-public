"""Screenplay converter: Movie Magic Screenwriter (.mmsw/.BK/.mmx), Fountain, Final Draft (.fdx), PDF.

Python 3.8+ standard library only.
"""
import os

from . import fdx, fountain, mmsw, mmx, pdf
from .model import NOTE, SCENE, CHARACTER

__version__ = '0.1.0'

READ_FORMATS = ('mmsw', 'mmx', 'fdx', 'fountain')
WRITE_FORMATS = ('fountain', 'fdx', 'mmsw', 'mmx', 'pdf')
EXTENSIONS = {'.fountain': 'fountain', '.spmd': 'fountain', '.txt': 'fountain', '.mmsw': 'mmsw',
              '.bk': 'mmsw', '.mmx': 'mmx', '.fdx': 'fdx', '.pdf': 'pdf'}
OUTPUT_EXTENSION = {'fountain': '.fountain', 'fdx': '.fdx', 'mmsw': '.mmsw', 'mmx': '.mmx', 'pdf': '.pdf'}


class ConversionError(Exception):
    pass


def detect(data, path=''):
    """Detect the format from the file content; the extension only breaks ties."""
    if mmsw.is_mmsw(data):
        return 'mmsw'
    if mmx.is_mmx(data):
        return 'mmx'
    if fdx.is_fdx(data):
        return 'fdx'
    if data.startswith(b'%PDF'):
        return 'pdf'
    if b'\x00' in data[:4096]:
        return 'unknown'
    return 'fountain'


def read(path, warnings=None):
    warnings = [] if warnings is None else warnings
    with open(path, 'rb') as f:
        data = f.read()
    fmt = detect(data, path)
    if fmt == 'mmsw':
        return mmsw.read(data, warnings), fmt
    if fmt == 'mmx':
        return mmx.read(data, warnings), fmt
    if fmt == 'fdx':
        return fdx.read(data, warnings), fmt
    if fmt == 'pdf':
        raise ConversionError('PDF files cannot be read; use the original screenplay file.')
    if fmt == 'unknown':
        raise ConversionError('Unknown file format. Supported: .mmsw, .BK, .mmx, .fdx, .fountain')
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        text = data.decode('cp1252', 'replace')
        warnings.append('the Fountain file was not UTF-8; read it as Windows-1252')
    return fountain.read(text), fmt


def render(script, fmt, paper='a4', warnings=None):
    warnings = [] if warnings is None else warnings
    notes = sum(1 for e in script.elements if e.type == NOTE)
    if fmt == 'fountain':
        return fountain.write(script).encode('utf-8')
    if fmt == 'fdx':
        if notes:
            warnings.append('%d script note(s) left out (Final Draft keeps notes outside the text)' % notes)
        return fdx.write(script)
    if fmt == 'mmsw':
        return mmsw.write(script)
    if fmt == 'mmx':
        return mmx.write(script)
    if fmt == 'pdf':
        if notes:
            warnings.append('%d script note(s) left out of the PDF' % notes)
        return pdf.write(script, paper=paper, warnings=warnings)
    raise ConversionError('Unknown output format: %s' % fmt)


def output_format(path):
    fmt = EXTENSIONS.get(os.path.splitext(path)[1].lower())
    if fmt is None or fmt not in WRITE_FORMATS:
        raise ConversionError('Cannot tell the output format from "%s". Use .fountain, .fdx, .mmsw, .mmx or .pdf'
                              % os.path.basename(path))
    return fmt


def summary(script):
    scenes = sum(1 for e in script.elements if e.type == SCENE)
    names = sorted({e.text.split('(')[0].strip().upper() for e in script.elements if e.type == CHARACTER})
    return {'elements': len(script.elements), 'scenes': scenes, 'characters': names,
            'title_page': script.has_title_page}
