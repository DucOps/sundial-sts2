# Changelog

All notable changes to Sundial are listed here. Versions follow [Semantic Versioning](https://semver.org/):
while it's `0.x`, any release may change things.

## [Unreleased]

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

[Unreleased]: https://github.com/DucOps/sundial-sts2/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/DucOps/sundial-sts2/releases/tag/v0.0.1
