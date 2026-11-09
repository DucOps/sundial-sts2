# Changelog

All notable changes to Sundial are listed here. Versions follow [Semantic Versioning](https://semver.org/):
while it's `0.x`, any release may change things.

## [Unreleased]

### Added
- Knowledge layer (`knowledge/`): card annotations (roles, mechanics, review status) and per-character archetype
  definitions, specified in `knowledge/SCHEMA.md` and checked by `knowledge/scripts/validate_knowledge.py` (JSON
  Schema plus cross-file checks; the smoke test runs it). Starts with Ironclad: four archetypes and 15 draft cards.
  `knowledge/scripts/game_card_ids.py` lists card ids from your game data for the validator's `--card-ids` check.
  The files ship inside the package. `pyyaml` is now a dependency; `jsonschema` is a dev dependency.
- Archetype detection in the run summary, computed by the server rather than inferred by the model: per deck
  snapshot (each card reward, shop and boss) the role counts and each archetype's enablers, payoffs, state (absent,
  forming, committed, half_built) and whether its support roles are met; per run, the primary archetype at each
  boss, when each archetype committed, pivots, half-built or under-supported archetypes at bosses, and orphan cards.
  New sections: **Deck roles and archetypes at each boss**, **Archetype timeline**, **Knowledge confidence** (draft,
  stale, unchecked and unannotated cards). New tool `get_deck_snapshots` shows every snapshot. `status` reports the
  annotations loaded.
- Game data entries carry a `text_hash`, so a card annotated on an older build is reported stale when its text has
  changed since (builder version 4; knowledge rebuilds once).

- Ironclad annotations: 23 cards (was 15), checked against the v0.111.0 text. Fixed drafts that didn't match it
  (Demon Form is a Strength enabler, not a payoff or keystone; Inferno both feeds and pays off self-damage; Burning
  Pact is deck thinning, not net draw; plain block cards no longer feed Barricade). Added Strength payoffs (Twin
  Strike, Sword Boomerang, Whirlwind, Conflagration) and block-retention cards (Stone Armor, Unmovable, Body Slam,
  Juggernaut).
- `knowledge/SCHEMA.md` §3 documents how the server resolves primary-archetype ties (a margin of 2), orphans and
  unannotated cards.
- Silent archetypes (draft): Poison, Shivs and Sly / discard in `knowledge/silent/archetypes.yaml`, with low
  first-guess thresholds. No Silent cards are annotated yet, so they're counted from card text.
- README: **Project status** and **Contributing to the analysis** sections.

### Changed
- Character notes are split into one file per character (`references/characters/<character>.md`) plus
  `_shared.md`; the analyst loads only the run character's file. Each has a coverage status (`partial` for Ironclad
  and Silent, `draft — not yet played` for Defect, Necrobinder and Regent). Tier-list opinions were removed (they're
  expert views), and cards that don't exist in v0.111 (Heavy Blade, Limit Break, Spot Weakness, Catalyst) dropped.
- The analyst skill reads archetype states, role counts and staleness from the run summary instead of inferring
  them, cites archetype facts under "Deck & draft", and reports draft, stale and unannotated cards under
  "Confidence" (flagged when more than ~3). Expert slot rules are unchanged.
- Role counts replace the keyword "Deck coverage" section. Cards without an annotation still use the old text
  heuristic and are marked `*`. The player summary's AoE/draw boss rates use the same counts.

## [0.0.5] - 2026-11-08

### Added
- Game knowledge builds itself: the MCP server builds it from your game install on first start and rebuilds it in
  the background after a game update (or a builder change). Builds take a few seconds, are saved per game version
  (`knowledge/game/game-<version>.json`), and a failed build keeps the last good one; `status` reports which version
  is loaded and any error. `STS2_GAME_DIR` and `STS2_AUTO_KNOWLEDGE=0` override it. `dnfile` is now a dependency.
- Powers (Vulnerable, Plating, Doom, ...) and keywords (Exhaust, Retain, Sly, ...) in the knowledge: `lookup` finds
  them, and the run summary's glossary explains the ones the deck's cards mention.
- Mechanics tags and a **Synergies** section in the run summary: for each mechanic (self-damage, exhaust,
  Vulnerable, Strength, Poison, Shivs, discard, orbs, Doom, Osty, Stars, Forge) which cards and relics feed it and
  which pay it off, with warnings for self-damage, discard or Stars fed with no payoff, and payoff cards passed.

### Changed
- The game-data importer moved into the package (`sundial_sts2/gamedata.py`) and is about 20× faster (lazy loading
  of `sts2.dll`). `tools/import_game_data.py` remains for manual rebuilds.
- The smoke test is hermetic: it no longer reads Steam Cloud saves or builds knowledge from a local game install.
- Test fixtures are now synthetic: `tests/fixtures/make_fixtures.py` builds a win, a death and an abandoned run from
  scratch with a fixed seed, so the repo holds no real player's runs. The demo data, README screenshots and the
  example analysis (`examples/analysis-1790200000`) were regenerated from them.
- README: a screenshot of the expert feature (the two shipped personas in Compare view). `build.py` takes
  `--analyses <dir>` so demo builds can include example analyses.

## [0.0.4] - 2026-11-08

### Fixed
- Runs played on another device were missed: the archive now also scans Steam Cloud's local copy
  (`Steam/userdata/<id>/2868840/remote`), which can be newer than the game's own save folder. Turn it off with
  `STS2_STEAM_CLOUD=0`.
- Game-data importer: card keywords given as a single value (e.g. Exhaust on Impervious, Unplayable on Injury and
  Wound) were dropped; amounts written as `{}` (Eternal Feather, Fishing Rod, Clarity) were blank; Shiv and
  Sovereign Blade showed a stray `AllEnemies:`; Ember Tea's combat count was missing; Mad Science now lists its
  Attack and Skill forms instead of `???`.

## [0.0.3] - 2026-11-08

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

[Unreleased]: https://github.com/DucOps/sundial-sts2/compare/v0.0.5...HEAD
[0.0.5]: https://github.com/DucOps/sundial-sts2/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/DucOps/sundial-sts2/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/DucOps/sundial-sts2/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/DucOps/sundial-sts2/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/DucOps/sundial-sts2/releases/tag/v0.0.1
