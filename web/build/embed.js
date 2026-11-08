// Parse folders of .run files into the compact model (for the embedded starter dataset).
// usage: node embed.js <out.json> <historyDir>:<profileName> [<historyDir>:<profileName> ...]
const fs = require('fs'), path = require('path');
const STS2 = require('../src/parse.js');
const [out, ...sources] = process.argv.slice(2);
const byKey = new Map();
for (const src of sources) {
  const i = src.lastIndexOf(':'); const dir = src.slice(0, i), profile = src.slice(i + 1);
  for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.run'))) {
    const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    if (STS2.looksLikeRun(d)) { const r = STS2.parseRun(d, { profile, file: f }); byKey.set(r.key + '|' + profile, r); }
  }
}
const runs = [...byKey.values()].sort((a, b) => a.start - b.start);
fs.writeFileSync(out, JSON.stringify(runs));
console.log(runs.length, 'runs', fs.statSync(out).size, 'bytes');
