#!/usr/bin/env python3
"""Convert screenplays between Movie Magic Screenwriter, Fountain, Final Draft and PDF.

Examples
  python3 convert.py script.mmsw script.fountain
  python3 convert.py script.fountain script.mmsw
  python3 convert.py script.mmsw script.pdf --paper letter
  python3 convert.py *.mmsw --to fdx --out-dir converted
  python3 convert.py script.mmsw --info

Reads .mmsw / .BK (Movie Magic 6 binary), .mmx (Movie Magic Mac XML), .fdx, .fountain.
Writes .fountain, .fdx, .mmsw (binary, readable by Windows and Mac Movie Magic),
.mmx (Movie Magic Mac only), .pdf (A4 by default).
Never overwrites an existing file unless --force is given; never writes over the input.
Everything runs locally; nothing is sent anywhere.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import screenplay_convert as sc  # noqa: E402


def convert_one(src, dst, fmt, args):
    warnings = []
    script, in_fmt = sc.read(src, warnings)
    if os.path.abspath(src) == os.path.abspath(dst):
        raise sc.ConversionError('Output would overwrite the input file: %s' % dst)
    if os.path.exists(dst) and not args.force:
        raise sc.ConversionError('Output already exists (use --force to replace it): %s' % dst)
    data = sc.render(script, fmt, paper=args.paper, warnings=warnings)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(data)
    s = sc.summary(script)
    print('OK  %s (%s) -> %s (%s): %d elements, %d scenes, title page: %s'
          % (src, in_fmt, dst, fmt, s['elements'], s['scenes'], 'yes' if s['title_page'] else 'no'))
    if fmt == 'mmsw':
        print('    note: the Movie Magic writer is new; open the file in Movie Magic and check it before relying on it')
    for w in sorted(set(warnings)):
        print('    warning: %s' % w)


def main(argv=None):
    p = argparse.ArgumentParser(description='Convert screenplays: Movie Magic (.mmsw/.BK/.mmx), Fountain, Final Draft (.fdx), PDF.')
    p.add_argument('files', nargs='+', help='INPUT OUTPUT, or several inputs with --to')
    p.add_argument('--to', choices=sc.WRITE_FORMATS, help='output format for one or more inputs')
    p.add_argument('--out-dir', help='folder for outputs when --to is used (default: next to each input)')
    p.add_argument('--paper', choices=('a4', 'letter'), default='a4', help='PDF paper size (default a4)')
    p.add_argument('--force', action='store_true', help='replace existing output files')
    p.add_argument('--info', action='store_true', help='only describe the input files')
    args = p.parse_args(argv)

    jobs = []
    try:
        if args.info:
            for src in args.files:
                warnings = []
                script, fmt = sc.read(src, warnings)
                s = sc.summary(script)
                print('%s: %s, %d elements, %d scenes, title page: %s' % (src, fmt, s['elements'], s['scenes'],
                                                                         'yes' if s['title_page'] else 'no'))
                print('    characters: %s' % (', '.join(s['characters']) or '-'))
                for w in sorted(set(warnings)):
                    print('    warning: %s' % w)
            return 0
        if args.to:
            for src in args.files:
                base = os.path.splitext(os.path.basename(src))[0]
                folder = args.out_dir or os.path.dirname(src)
                jobs.append((src, os.path.join(folder, base + sc.OUTPUT_EXTENSION[args.to]), args.to))
        elif len(args.files) == 2:
            jobs.append((args.files[0], args.files[1], sc.output_format(args.files[1])))
        else:
            p.error('give INPUT OUTPUT, or use --to FORMAT with one or more inputs')
    except (sc.ConversionError, OSError) as e:
        print('ERROR %s' % e, file=sys.stderr)
        return 1

    failed = 0
    for src, dst, fmt in jobs:
        try:
            convert_one(src, dst, fmt, args)
        except (sc.ConversionError, OSError, ValueError) as e:
            failed += 1
            print('ERROR %s: %s' % (src, e), file=sys.stderr)
        except Exception as e:  # keep going in batch mode, but say what broke
            failed += 1
            print('ERROR %s: unexpected %s: %s' % (src, type(e).__name__, e), file=sys.stderr)
    if len(jobs) > 1:
        print('%d converted, %d failed' % (len(jobs) - failed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
