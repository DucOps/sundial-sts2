# Sundial (sundial-sts2)

Slay the Spire 2 run-history tool. **Primary:** the single-file HTML dashboard (run history, per-run detail,
climb, patches, stats), which needs no install. **Secondary, optional:** a Python package that archives runs and
an MCP server for AI post-game analysis with user-written expert cards. Keep the dashboard fully usable without the
AI side, and keep AI features opt-in and out of the way (e.g. the analysis panel only appears when an analysis is
imported).
Display name **Sundial**; internal name **sundial-sts2** everywhere (package, command, MCP server, data folder) so it
isn't confused with other "sundial" projects. Unofficial fan project, not affiliated with Mega Crit.

## Layout
- `src/sundial_sts2/`
  - `parse.py`: `.run` JSON → `Run`/`Floor` dataclasses.
  - `store.py`: finds save folders, archives new runs to `~/.sundial-sts2/archive`, one-time migration from `~/.spire-ledger`.
  - `analysis.py`: run digest, baselines, roles/archetype timeline, deciding fights' enemies, player summary.
  - `knowledge.py`: loads game knowledge (cards, relics, potions, powers, keywords) and the user's own files.
  - `gamedata.py`: builds that knowledge from the user's game install (`.pck` text + `sts2.dll` values via dnfile);
    the server rebuilds it in a background thread when the game version or `BUILDER_VERSION` changes. Bump
    `BUILDER_VERSION` whenever the output changes. Never ship its output.
  - `gameworld.py`: the rest of the game facts from the same install (characters, monsters and their moves,
    encounters, acts, orbs, ascension levels, glossary). Ascension-dependent numbers are `{base, asc, from}`.
  - `annotations.py`: loads `knowledge/` annotations; role counts, archetype states, orphans and staleness per deck
    (SCHEMA.md §3). The per-run timeline (`archetype_report`) is in `analysis.py`.
  - `mechanics.py`: enabler/payoff rules per mechanic, used to tag entries and for the digest's Synergies section.
  - `experts.py`: expert cards and enabled slots.
  - `server.py`: the MCP tools and prompts.
- `knowledge/`: descriptive card annotations and archetypes per character (`SCHEMA.md` is the spec). Card ids are the
  game-data ids lower-cased. Validate with `uv run python knowledge/scripts/validate_knowledge.py knowledge` (add
  `--card-ids` from `knowledge/scripts/game_card_ids.py`; never commit that list). Ships in the wheel as
  `sundial_sts2/annotations`. Changing roles or field meanings needs a `schema_version` bump.
- `.claude/skills/sundial-sts2-analyst/`: the analysis skill. It's the single source of truth; it's also zipped for Claude Desktop.
- `web/`: the dashboard.
  - `web/src/app.html` + `web/src/parse.js` (a JS port of the parser) are built by `web/build/build.py` into `web/dist/`.
  - Vanilla JS, hand-made SVG charts; the only external script is JSZip from cdnjs.
- `experts/`: example cards (`steady-hand`, `greedy-climber` personas; `house-rules` personal). Template: `src/sundial_sts2/expert_template.md`. Guide: `docs/creating-an-expert.md`.
- `docs/ai-analysis.md`: the tinkerer's guide to the AI analysis (layers, run summary sections, schemas, recipes).
  Keep it in step when the summary, schema or skill changes.
- `tests/smoke.py` + `tests/fixtures/history/*.run` (a win, a death, an abandoned run) + `tests/test_*.py` (pytest,
  same fixtures, `tests/conftest.py` points the package at a throwaway data folder). The fixtures are synthetic,
  made by `tests/fixtures/make_fixtures.py`; never replace them with real runs.
- `local/`: private and gitignored (personal tools and cards). Never reference it from public docs, never commit it.

## Commands
- Set up: `uv sync`
- Smoke test (run after any change to `src/`): `uv run python tests/smoke.py`
- Unit tests: `uv run python -m pytest tests/` (hermetic; they set their own `SUNDIAL_HOME` and archive)
- Run the server by hand: `uv run sundial-sts2` (stdio; waits silently)
- Dashboard:
  - Blank build: `python web/build/build.py --empty` → `web/dist/sundial-blank.html`.
  - With your runs: `node web/build/embed.js web/build/runs.json <history dir>:profile1`, then `python web/build/build.py`.
  - The embedded build `web/dist/sundial.html` contains personal data; it's gitignored.
  - README screenshots (`docs/images/`) use fake data: `python web/build/demo.py <dir>`, then
    `node web/build/embed.js web/build/demo-runs.json <dir>:demo tests/fixtures/history:demo` and
    `python web/build/build.py --data web/build/demo-runs.json --out sundial-demo.html --analyses <dir with
    examples/analysis-*.json>`, then screenshot `#overview`, `#runs`, `#run-<key>`, `#climb` at 1280px wide
    (headless Edge `--screenshot` works). `experts-compare.png` is the analysis panel of the fixture win
    (`#run-TQ1P1U5C99XJ-1790200000`) with `localStorage['sts2-ledger-anview-v1'] = {"mode":"compare","off":["core"]}`
    and everything but `#analysis` hidden.
  - Analysts demo: the same demo runs built with `--out sundial-demo-analysts.html --analyses web/build/demo/analyses`
    (hand-written analyses of the 10 newest demo runs, including the fictional custom expert
    `web/build/demo/experts/slow-burn`). They match `demo.py`'s fixed seed; rewrite them if its output changes.
  - Both demo builds (`sundial-demo.html` without `--analyses`, `sundial-demo-analysts.html`) are committed: the README
    links to them on GitHub Pages (served from `main`, repo root; `.nojekyll` keeps files as-is). They hold only generated data.

## Versioning
- Semantic versioning, starting at 0.0.1. The single source is `__version__` in `src/sundial_sts2/__init__.py`:
  `pyproject.toml` reads it (hatch dynamic version), the MCP server reports it, and `build.py` stamps it into the
  dashboard footer.
- Log changes under `## [Unreleased]` in `CHANGELOG.md` as they land.
- To release: bump `__version__`, move Unreleased into a dated `## [x.y.z]` section (update the compare links),
  update the version in the README's Versions section, rebuild `web/dist/sundial-blank.html` and the two demo builds, run the smoke test,
  commit, then `git tag -a vX.Y.Z -m "Sundial X.Y.Z"` and `git push --follow-tags`.

## Conventions
- The parser exists twice (`parse.py` and `web/src/parse.js`). Keep them in step: for example, shop stock is never counted as a skipped card reward.
- MCP SDK v2: `MCPServer`, `@mcp.tool`, `@mcp.prompt`. Raise `ToolError` (`mcp.server.mcpserver.exceptions`) for expected errors, not `ValueError`.
- The Sundial analyst (the core analysis; `core` in saved-analysis data) is character-neutral and uses the player's own baselines. Experts are user-written viewpoints. Never ship cards that speak for a real person.
- Saved analyses: `~/.sundial-sts2/analyses/<run_id>.json`, `type: "sundial-sts2-analysis"`. The dashboard also accepts the old `spire-ledger-analysis` type.
- Dashboard `localStorage` keys keep their old `sts2-ledger-*` names on purpose, so browser data carries over.
- The game prunes `saves/history`. Never delete from the archive.

## Data notes
- Save files:
  - Windows: `%APPDATA%\SlayTheSpire2\steam\<SteamID>\profileN\saves\history\*.run` (`.run.backup` files are duplicates).
  - macOS/Linux paths are unverified.
- `.run` schema v9/v10. Per-floor stats are in `map_point_history[act][i].player_stats`.
