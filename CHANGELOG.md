# Changelog

All notable changes to Sundial are listed here. Versions follow [Semantic Versioning](https://semver.org/):
while it's `0.x`, any release may change things.

## [Unreleased]

### Added
- `tools/import_game_data.py`: builds card, relic and potion knowledge from your own game install (text from
  `SlayTheSpire2.pck`, numbers, costs, upgrades, rarity and character from `sts2.dll`), so `lookup` and deck
  coverage work on the current patch. Run with `uv run --with dnfile`; writes `~/.sundial-sts2/knowledge/game.json`.
  The data stays on your machine; game updates may break the importer and future support isn't guaranteed.

## [0.0.2] - 2026-11-08

### Added
- README screenshots, made from generated demo data (`web/build/demo.py`).
- `build.py` takes `--data` and `--out`, so demo builds never touch your personal `runs.json`.

### Changed
- Analyst skill: much fuller character notes (kits, mechanics, archetypes, coverage, typical failures for all
  five characters, plus Aeonglass and Artifact), from community guides for v0.107 to v0.111.
- The skill reads the character notes for every run, not only non-Ironclad ones.
- README: new "Character notes" section on what the file is for, how it was made and how to improve it.

## [0.0.1] - 2026-11-08

First release.

### Dashboard
- Single-file HTML dashboard, no install: Overview, Runs, Cards, Climb, Patches, Relics & Ancients, Fights and Data.
- Per-run detail with HP chart, path, deck, relics and a floor-by-floor log.
- Import `.run` files, folders or zips from several devices; re-imports only add new runs.

### Archive and analysis (optional)
- Python package that archives runs to `~/.sundial-sts2/archive`, since the game prunes its history.
- MCP server for AI post-game analysis, using your own runs as the baseline.
- Expert cards: example personas (`steady-hand`, `greedy-climber`) and a template for writing your own.

[Unreleased]: https://github.com/DucOps/sundial-sts2/compare/v0.0.2...HEAD
[0.0.2]: https://github.com/DucOps/sundial-sts2/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/DucOps/sundial-sts2/releases/tag/v0.0.1
