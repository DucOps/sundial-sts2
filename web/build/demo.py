#!/usr/bin/env python3
"""Generate a fake but plausible run history for README screenshots.

Takes the fixture runs in tests/fixtures/history and varies them: dates over about three months, ascension climbing
as runs are won, game builds by date, and deaths cut at a fight with that encounter as the killer. No real player
data is used beyond the three fixtures already in the repo.

usage: python web/build/demo.py <out dir> [count]     (default 140 runs, fixed seed so output is repeatable)
Then:  node web/build/embed.js web/build/demo-runs.json <out dir>:demo
       python web/build/build.py --data web/build/demo-runs.json --out sundial-demo.html
"""
import copy, json, pathlib, random, sys

root = pathlib.Path(__file__).resolve().parents[2]
fixtures = root / 'tests/fixtures/history'
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
count = int(sys.argv[2]) if len(sys.argv) > 2 else 140
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


asc, wins_at_asc, start = 0, 0, 1786000000                    # mid-Aug 2026
for i in range(count):
    start += rng.randint(2 * 3600, 30 * 3600)
    p_win = max(0.04, 0.42 - asc * 0.042)
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
        wins_at_asc += 1
        if asc < 10:
            asc, wins_at_asc = asc + 1, 0

print(count, 'demo runs in', out, '- reached ascension', asc)
