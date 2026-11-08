#!/usr/bin/env python3
"""Assemble dist/sundial.html from src/app.html + src/parse.js (+ optional starter data)."""
import pathlib, sys
root = pathlib.Path(__file__).resolve().parent.parent
html = (root / 'src/app.html').read_text(encoding='utf-8')
parser = (root / 'src/parse.js').read_text(encoding='utf-8')
data_path = root / 'build/runs.json'
data = data_path.read_text(encoding='utf-8') if (len(sys.argv) < 2 or sys.argv[1] != '--empty') and data_path.exists() else '[]'
data = data.replace('</', '<\\/')
an_dir = root / 'build/analyses'
an = '[]'
if data != '[]' and an_dir.exists():
    import json as _j
    an = _j.dumps([_j.loads(f.read_text(encoding='utf-8')) for f in sorted(an_dir.glob('*.json'))], ensure_ascii=False).replace('</', '<\\/')
out = html.replace('/*__PARSER__*/', parser).replace('/*__DATA__*/', data).replace('/*__ANALYSES__*/', an)
name = 'sundial.html' if data != '[]' else 'sundial-blank.html'
(root / 'dist').mkdir(exist_ok=True)
(root / 'dist' / name).write_text(out, encoding='utf-8')
print(name, len(out))
