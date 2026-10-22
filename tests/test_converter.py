"""Tests on the invented sample script: python3 -m unittest discover tests"""
import os
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, '..', 'plugin', 'skills', 'screenplay-convert', 'scripts')
sys.path.insert(0, SCRIPTS)

import screenplay_convert as sc  # noqa: E402
from screenplay_convert import fdx, fountain, mmsw, mmx, pdf  # noqa: E402
from screenplay_convert.model import ACTION, CENTERED, CHARACTER, PAGEBREAK, PAREN, SCENE, TRANSITION, NOTE  # noqa: E402

SAMPLE = os.path.join(HERE, 'fixtures', 'sample.fountain')


def load():
    with open(SAMPLE, encoding='utf-8') as f:
        return fountain.read(f.read())


def comparable(script, notes=True):
    out = []
    for e in script.elements:
        if (e.type == NOTE and not notes) or e.type == PAGEBREAK:
            continue
        text = ' '.join(e.text.split())
        if e.type == PAREN:
            text = text.strip('()')
        if e.type in (SCENE, CHARACTER, TRANSITION):
            text = text.upper()
        etype = ACTION if e.type == CENTERED else e.type      # Movie Magic has no centered text element
        out.append((etype, text, tuple(sorted(s for _, st in e.runs for s in st))))
    return out


class FountainReading(unittest.TestCase):
    def test_elements(self):
        s = load()
        types = [e.type for e in s.elements]
        self.assertIn(SCENE, types)
        self.assertEqual(s.elements[2].text, 'Sumu nousee järveltä. ÄITI (60) kantaa vesisankoa laiturilta kohti saunaa – hitaasti, varovasti.')
        names = [e.text for e in s.elements if e.type == CHARACTER]
        self.assertEqual(names[:2], ['ÄITI', 'EERO (O.S.)'])
        self.assertTrue(any(e.dual for e in s.elements if e.type == CHARACTER))
        self.assertEqual(s.title_block[0], 'TESTIKÄSIKIRJOITUS')
        self.assertIn('test@example.com', s.contact_block)

    def test_emphasis(self):
        s = load()
        action = s.elements[2]
        self.assertIn(('varovasti', frozenset({'italic'})), action.runs)
        underlined = [t for e in s.elements for t, st in e.runs if 'underline' in st]
        self.assertEqual(underlined, ['vanha valokuva'])


class RoundTrips(unittest.TestCase):
    def roundtrip(self, write, read, notes=True):
        s = load()
        back = read(write(s))
        self.assertEqual(comparable(back, notes), comparable(s, notes))
        return back

    def test_mmsw(self):
        back = self.roundtrip(mmsw.write, mmsw.read)
        self.assertEqual(back.title_block[0], 'TESTIKÄSIKIRJOITUS')

    def test_mmsw_layout(self):
        data = mmsw.write(load())
        self.assertTrue(data.startswith(b'ScreenwriterWinVer. 6.00'))
        self.assertEqual(data[-2:], b'\x00\x00')
        self.assertEqual(len(data[:mmsw.HEADER_SIZE]), 28208)

    def test_mmx(self):
        self.roundtrip(mmx.write, mmx.read)
        self.assertTrue(zlib.decompress(mmx.write(load())).startswith(b'<?xml'))

    def test_fdx(self):
        back = self.roundtrip(fdx.write, fdx.read, notes=False)
        self.assertEqual(back.title_block[0], 'TESTIKÄSIKIRJOITUS')

    def test_fountain(self):
        self.roundtrip(lambda s: fountain.write(s), fountain.read)


class Pdf(unittest.TestCase):
    def test_pdf(self):
        data = pdf.write(load())
        self.assertTrue(data.startswith(b'%PDF-1.4'))
        self.assertTrue(data.rstrip().endswith(b'%%EOF'))
        self.assertIn(b'/MediaBox [0 0 595.28 841.89]', data)
        self.assertIn(b'/MediaBox [0 0 612.00 792.00]', pdf.write(load(), paper='letter'))

    def test_long_dialogue_splits(self):
        s = fountain.read('INT. HUONE - PÄIVÄ\n\nANNA\n' + ' '.join(['Sana'] * 900) + '\n')
        data = pdf.write(s)
        streams = data.count(b'/FlateDecode')
        self.assertGreater(streams, 2)
        body = b''.join(zlib.decompress(part.split(b'stream\n', 1)[1].rsplit(b'\nendstream', 1)[0])
                        for part in data.split(b'obj\n')[1:] if b'/FlateDecode' in part)
        self.assertEqual(body.count(b'\\(MORE\\)'), body.count(b"ANNA \\(CONT'D\\)"))
        self.assertGreaterEqual(body.count(b'\\(MORE\\)'), 2)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, 'convert.py')] + list(args),
                              capture_output=True, text=True)

    def test_convert_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'sample.mmsw')
            r = self.run_cli(SAMPLE, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = self.run_cli(SAMPLE, out)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('already exists', r.stderr)
            r = self.run_cli(out, os.path.join(d, 'back.fountain'))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_refuses_input_as_output(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 'a.fountain')
            with open(src, 'w', encoding='utf-8') as f:
                f.write('INT. A - B\n\nText.\n')
            r = self.run_cli(src, src, '--force')
            self.assertNotEqual(r.returncode, 0)

    def test_batch(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli(SAMPLE, '--to', 'pdf', '--out-dir', d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(os.path.join(d, 'sample.pdf')))


if __name__ == '__main__':
    unittest.main()
