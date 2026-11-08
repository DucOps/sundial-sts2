#!/usr/bin/env python3
"""Assemble dist/sundial.html from src/app.html + src/parse.js (+ optional starter data)."""
import pathlib, re, sys
root = pathlib.Path(__file__).resolve().parent.parent
html = (root / 'src/app.html').read_text(encoding='utf-8')
parser = (root / 'src/parse.js').read_text(encoding='utf-8')
# usage: build.py [--empty] [--data <runs.json>] [--out <name.html>] [--analyses <dir>]
args = sys.argv[1:]
def opt(flag):
    return args[args.index(flag) + 1] if flag in args else None
data_path = pathlib.Path(opt('--data')) if opt('--data') else root / 'build/runs.json'
data = data_path.read_text(encoding='utf-8') if '--empty' not in args and data_path.exists() else '[]'
data = data.replace('</', '<\\/')
an_dir = pathlib.Path(opt('--analyses')) if opt('--analyses') else root / 'build/analyses'
an = '[]'
# personal analyses only go into the personal build; demo builds take them from --analyses (e.g. examples/)
if data != '[]' and (opt('--analyses') or not opt('--data')) and an_dir.exists():
    import json as _j
    an = _j.dumps([_j.loads(f.read_text(encoding='utf-8')) for f in sorted(an_dir.glob('*.json'))], ensure_ascii=False).replace('</', '<\\/')
init = (root.parent / 'src/sundial_sts2/__init__.py').read_text(encoding='utf-8')
version = re.search(r'__version__ = "([^"]+)"', init).group(1)
out = html.replace('/*__VERSION__*/', version).replace('/*__PARSER__*/', parser).replace('/*__DATA__*/', data).replace('/*__ANALYSES__*/', an)
name = opt('--out') or ('sundial.html' if data != '[]' else 'sundial-blank.html')
(root / 'dist').mkdir(exist_ok=True)
(root / 'dist' / name).write_text(out, encoding='utf-8')
print(name, len(out))
