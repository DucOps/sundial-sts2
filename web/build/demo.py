#!/usr/bin/env python3
"""Generate a fake but plausible run history for README screenshots.

Takes the fixture runs in tests/fixtures/history and varies them: dates over about three months, ascension climbing
as runs are won, game builds by date, and deaths cut at a fight with that encounter as the killer. No real player
data is used beyond the three fixtures already in the repo.

The story: Ironclad climbs to A10 (with the odd try of another character), then play shifts mostly to Silent, with
some Defect, Necrobinder and Regent. Each character has its own ascension. The fixtures are all Ironclad, so other
characters get their own starter Strike/Defend ids but otherwise keep Ironclad cards; that only shows when you open
one of those runs, so screenshot an Ironclad run for the run detail.

usage: python web/build/demo.py <out dir> [count]     (default 160 runs, fixed seed so output is repeatable)
Then:  node web/build/embed.js web/build/demo-runs.json <out dir>:demo
       python web/build/build.py --data web/build/demo-runs.json --out sundial-demo.html
"""
import copy, json, pathlib, random, sys

root = pathlib.Path(__file__).resolve().parents[2]
fixtures = root / 'tests/fixtures/history'
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
count = int(sys.argv[2]) if len(sys.argv) > 2 else 160
rng = random.Random(2026)

runs = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(fixtures.glob('*.run'))]
winner = next(r for r in runs if r['win'])
bases = [r for r in runs if not r['was_abandoned']]          # full-length runs to cut deaths from
BUILDS = ['v0.98.0', 'v0.101.2', 'v0.104.0', 'v0.107.1', 'v0.111.0']
SEED_CHARS = '0123456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def cut(run: dict, floor_index: int) -> dict:
    """Keep floors up to floor_index (0-based across acts) and end the run there."""
    hist, n = [], floor_index
    for act in run['map_point_history']:
        if n < len(act):
            hist.append(act[:n + 1]); break
        hist.append(act); n -= len(act)
    run['map_point_history'] = hist
    return run


def fights(run: dict) -> list[tuple[int, dict]]:
    pts = [pt for act in run['map_point_history'] for pt in act]
    return [(i, pt) for i, pt in enumerate(pts) if pt.get('rooms') and pt['rooms'][0].get('room_type') in ('monster', 'elite', 'boss')]


def pick_character(ironclad_done: bool) -> str:
    if not ironclad_done:
        return rng.choices(['IRONCLAD', 'SILENT', 'DEFECT'], [92, 5, 3])[0]
    return rng.choices(['IRONCLAD', 'SILENT', 'DEFECT', 'NECROBINDER', 'REGENT'], [28, 46, 14, 6, 6])[0]


def recolour(run: dict, char: str) -> None:
    p = run['players'][0]
    p['character'] = f'CHARACTER.{char}'
    for c in p['deck']:
        c['id'] = c['id'].replace('_IRONCLAD', f'_{char}')


ascs = {c: 0 for c in ('IRONCLAD', 'SILENT', 'DEFECT', 'NECROBINDER', 'REGENT')}
ironclad_done = False                                         # set once Ironclad wins at A10
start = 1785740000                                            # early Aug 2026
for i in range(count):
    start += rng.randint(2 * 3600, 30 * 3600)
    char = pick_character(ironclad_done) if i else 'IRONCLAD'
    asc = ascs[char]
    # other characters climb a bit faster: the player already knows the game
    p_win = max(0.04, (0.42 if char == 'IRONCLAD' else 0.55) - asc * 0.042)
    roll = rng.random()
    if roll < p_win:
        run = copy.deepcopy(winner)
    else:
        run = copy.deepcopy(rng.choice(bases))
        fs = fights(run)
        # deaths cluster at bosses and elites, and earlier at higher ascension
        weights = [(6 if pt['rooms'][0]['room_type'] == 'boss' else 3 if pt['rooms'][0]['room_type'] == 'elite' else 1)
                   * (1.6 if idx < 17 else 1.0) for idx, pt in fs]
        idx, pt = rng.choices(fs, weights)[0]
        run = cut(run, idx)
        last = run['map_point_history'][-1][-1]['player_stats'][0]
        last['damage_taken'] = last.get('damage_taken', 0) + last.get('current_hp', 0)
        last['current_hp'] = 0
        run.update(win=False, was_abandoned=False, killed_by_encounter=pt['rooms'][0]['model_id'], killed_by_event='NONE.NONE')
        if rng.random() < 0.07:                               # the odd abandoned run
            run.update(was_abandoned=True, killed_by_encounter='NONE.NONE')
    recolour(run, char)
    floors = sum(len(a) for a in run['map_point_history'])
    run.update(
        ascension=asc,
        start_time=start,
        run_time=int(floors * rng.uniform(70, 190)),
        seed=''.join(rng.choice(SEED_CHARS) for _ in range(12)),
        build_id=BUILDS[min(len(BUILDS) - 1, i * len(BUILDS) // count)],
    )
    (out / f'{start}.run').write_text(json.dumps(run), encoding='utf-8')
    if run['win']:
        if asc < 10:
            ascs[char] = asc + 1
        elif char == 'IRONCLAD':
            ironclad_done = True

print(count, 'demo runs in', out, '- ascension reached:', ', '.join(f'{c.title()} A{a}' for c, a in ascs.items()))
