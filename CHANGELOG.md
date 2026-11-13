# Changelog

All notable changes to Sundial are listed here. Versions follow [Semantic Versioning](https://semver.org/):
while it's `0.x`, any release may change things.

## [Unreleased]

## [0.1.0] - 2026-11-13

Support for Slay the Spire 2 v0.113 (beta): The Fool, the Blitz and Dread modes and save format v11.

### Added
- **The Fool** (v0.113, beta branch). Its cards and relics come from your game install like every other
  character's; the text tagging now knows its mechanics (Arrows and Aim, Melodies, Sadness, Stretch), so the run
  summary's Synergies section and generated archetypes cover it. The Fool's Strike and Defend show as Strike and
  Defend. The analyst skill has a draft character note for it.
- **Game modes.** Blitz and Dread (v0.113) are kept apart from Standard runs, and so are Daily runs:
  - Dashboard: a Mode filter, on Standard by default, appears once you've played more than one mode; the
    Ascension and Character filters follow it. Non-Standard runs are labelled (Blitz 3), and Climb picks a mode.
  - AI analysis: baselines, encounter history, `player_summary` and `ascension_climb` only compare runs of the same
    mode (Standard by default; `mode` to change it), `list_runs` can filter by mode, and the run summary's header
    names the mode. Dread enemies are shown at A10, Blitz enemies at base values.
  - Blitz runs read right: the three cards taken at Neow count as picks (the save lists only the ones left behind),
    and the merchant shows the services you took and passed on. Its card choices count as card rewards, not shop stock.
  - Custom games (marked in the save from v0.113) are their own mode, Custom, and never mix into Standard baselines
    or the climb.
- **Blitz analyses are lighter and tunable.** The analyst says up front that a Blitz analysis is optional (Standard
  is where your baselines are) and follows its own Blitz notes: judge Neow, the merchant services and the fixed
  elite and boss, never routing, elite counts or gold. Expert cards can add a `### Blitz` section under
  `## Mode notes` and a `modes` list; without Blitz notes, your own persona and personal cards apply minus their
  routing and gold principles, and creator or community cards are marked not applicable.
  `player_summary(mode="blitz")` lists the merchant services you take and your Neow picks.
- **Save format v11** (v0.113) is read; the Neow and merchant changes above are what it adds.
- **`card_history`**, a new AI tool for one card across your runs: how often it was offered at card rewards and how
  often you took it (picks, not runs), shop buys and other gains, whether it was still in the final deck, and how
  runs that took it or passed on it ended. For questions like "should I take Offering?".
- **Find fights and cards by part of a name.** `encounter_history("Parasite")` finds Phrog Parasite, and a name that
  matches nothing gets "did you mean" suggestions; `card_history` matches the same way.
- **`get_lessons` names the character** of each lesson when you don't filter by one.
- **pytest suite** (`uv run python -m pytest`): the parser on malformed saves, the archive, the tools' input
  checks and mode handling, v11 saves (a synthetic Fool run and Blitz win in `tests/fixtures/modes/`) including a
  check that the dashboard's parser reads them the same way, the cross-run tables, expert cards and the knowledge
  layer. pytest is in the `dev` group.

### Fixed
- **An expert's name could point outside the experts folder.** `save_expert_card`, `get_expert`,
  `set_expert_enabled` and `list_expert_sources` used the name as given, so a name like `../../x` could write or read
  outside `~/.sundial-sts2/experts`. Names must now be plain (lowercase letters, digits and hyphens).
- **A run could disappear from the archive without a word.** One reward entry the parser didn't expect (a card
  choice without its card, a list stored as an object, a null) made the whole run unreadable, and unreadable files
  were skipped silently. Every save field is now read defensively, in the server and the dashboard alike, so an
  odd entry costs only that entry. Files that really can't be read stay in the archive and are named: `status`
  reports `runs_unreadable` and an `unreadable` list, and `list_runs` and `get_run_summary` mention them.
- **`list_runs(limit=0)` returned every run** and a negative limit returned the oldest runs. `limit`,
  `player_summary`'s `last_n` and `patch_notes`' `limit` now must be 1 or more.
- **`patch_notes(since=...)` filtered everything out** for a date like `2026` or `2026-8-1`; it now asks for
  `YYYY-MM-DD`. An empty `since` still means no filter, and notes without a date no longer raise.
- **`get_lessons` failed on a hand-edited `lessons.json`.** Entries without a date show as undated; entries without
  text are skipped and counted.
- **A first run read "compared with your 0 finished runs".** The run summary now says there is no baseline yet,
  and the "typical" column is left empty instead of showing 0%.
- **Some fights were missing from the floor log and encounter history.** A fight is now recognised by its room
  type, so encounters without the usual ending in their id count too: Overgrowth Crawlers and event fights such as
  Punch Off and Dense Vegetation.
- **The skip rate counted some choices that weren't skips.** A `?` room that turned out to be a shop had its stock
  counted as a skipped card reward. Events where you choose cards (Room Full of Cheese, Brain Leech) list only the
  cards left behind, so the cards you took now count as picks. A card choice given by an Ancient's relic (Hefty
  Tablet and the like) marks no pick in the save, so it's no longer counted as a skip.
- **Wrong boss numbers from v0.113 game data.** Some boss HP and move values now add a bonus in Dread, which the
  game data reader misread (The Insatiable showed 20 HP instead of 321). Values are now read as outside Dread, and
  Dread runs add the boss HP bonus.
- **An A0 run compared with "A-1–A1".** The range starts at A0, and an empty "typical" HP cell shows "—", not "—%".

Thanks to the reports in [#1](https://github.com/DucOps/sundial-sts2/pull/1), which found the lost-run, `limit` and
`patch_notes` problems and suggested `card_history` and part-name matching. These are written from those reports, not
from the pull request's code.

## [0.0.8] - 2026-11-10

### Added
- **Settings** on the Data tab, now called Data & settings. The first one: put a run's post-game analysis at the
  top of its page, under the header, instead of at the bottom.

### Fixed
- **Filter bar showing where it does nothing.** The run page, Data & settings and Climb now hide the filters, as
  intended.

## [0.0.7] - 2026-11-10

### Added
- **Live demos**, linked from the README and served with GitHub Pages: the run tracker on its own, and the same
  generated runs with AI post-game analyses of the 10 most recent. The analyses show the two example personas
  and a fictional custom expert, The Slow Burn, to show that experts are yours to write.

### Fixed
- **Profile filter undercounting.** Importing a folder or zip whose paths don't name a `profileN` folder (for
  example the `history` folder itself) cleared the profile on runs the dashboard already knew, so they only showed
  under All. Imports now keep a known profile, the built-in history replaces older copies saved in the browser, and
  runs with no profile get an "Unknown" option.

## [0.0.6] - 2026-11-09

The run ledger is unchanged. This release is about the optional AI post-game analysis: it now works from the game's
own facts and computes what it can instead of leaving it to the AI.

### Added
- **More game facts from your install** (builder version 5; your knowledge rebuilds once on first start):
  characters (starting HP, gold, deck and relic), monsters (HP and every move's intents, powers, status cards and
  numbers, with ascension variants such as "Ebb Damage 22 (26 from A9)"), encounters (room type, monsters, act),
  acts (bosses, Ancients, events), events and Ancients (options with their numbers), orbs, enchantments, ascension
  levels and the game's glossary. `lookup` covers all of them. Values the reader can't evaluate are left out, never
  guessed.
- **Official patch notes** that ship with the game are saved beside the game data. New tool `patch_notes` searches
  them, e.g. when a card or enemy changed.
- **Run summary sections:**
  - the character's starting kit;
  - **Enemies in the deciding fights:** the fight that killed you, the bosses, and fights well above your usual
    damage, with HP and move numbers at the run's own ascension;
  - **Deck roles and archetypes at each boss**, **Archetype timeline** and **Knowledge confidence** (below);
  - the glossary now explains the events and Ancients the run visited.
- **Roles and archetypes, computed by the server.** Each deck snapshot (every card reward, shop and boss) gets role
  counts (front-load, AoE, scaling, block, draw, energy, debuff, sustain, card gen, deck thin) and, per archetype,
  its enablers, payoffs, state (absent, forming, committed, half-built) and whether its support roles are met. Per
  run: the primary archetype at each boss, when each archetype committed, pivots, half-built or under-supported
  archetypes at bosses, and orphan cards. New tool `get_deck_snapshots` shows every snapshot.
- **Archetypes for every character, generated from game text:** one per mechanic the character's own cards both
  feed and pay off (e.g. Orbs for Defect; Osty / Summon, Doom and Exhaust for Necrobinder; Stars, Forge and Exhaust
  for Regent).
- **Knowledge layer** (`knowledge/`, spec in `knowledge/SCHEMA.md`): hand-written archetypes and card annotations
  that override what text tagging finds. Ironclad has four archetypes and 23 draft card annotations checked
  against v0.111.0; Silent has draft Poison, Shivs and Sly / discard archetypes. Annotations carry a review status
  and the build they were checked on; the report says how many draft, stale or text-counted cards it relied on.
  `knowledge/scripts/validate_knowledge.py` checks the files (the smoke test runs it). The folder ships inside the
  package.
- **Guide for tinkerers,** [`docs/ai-analysis.md`](docs/ai-analysis.md): how the analysis fits together, every
  section of the run summary, the schemas and why they're built that way, where things are saved, and recipes for
  changing archetypes, card annotations, character notes, experts and the report.
- Dependencies: `pyyaml` (runtime) and `jsonschema` (dev).

### Changed
- The core analysis is now called the **Sundial analyst** everywhere you read it: the skill, the report, the
  dashboard's analysis panel and the docs. Saved analyses keep their `core` field, so older files and dashboard
  settings still work.
- Role counts replace the keyword-based "Deck coverage" section. Cards without an annotation are still counted from
  their text and marked `*`. The player summary's AoE/draw boss rates use the same counts.
- Character notes are split into one file per character plus `_shared.md`; the analyst loads only the run
  character's file. They're descriptive only, each with a coverage status (`partial` for Ironclad and Silent,
  `draft — not yet played` for Defect, Necrobinder and Regent). Tier-list opinions were removed (they're expert
  views), and cards that don't exist in v0.111 (Heavy Blade, Limit Break, Spot Weakness, Catalyst) were dropped.
- The analyst skill cites the computed archetype facts under "Deck & draft" and reports draft, stale and
  unannotated cards under "Confidence". Expert slot rules are unchanged.
- README: Sundial is presented as a run ledger first; the AI post-game analysis is a clearly separate side
  experiment with a short setup section and a link to the guide.

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

[Unreleased]: https://github.com/DucOps/sundial-sts2/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/DucOps/sundial-sts2/compare/v0.0.8...v0.1.0
[0.0.8]: https://github.com/DucOps/sundial-sts2/compare/v0.0.7...v0.0.8
[0.0.7]: https://github.com/DucOps/sundial-sts2/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/DucOps/sundial-sts2/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/DucOps/sundial-sts2/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/DucOps/sundial-sts2/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/DucOps/sundial-sts2/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/DucOps/sundial-sts2/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/DucOps/sundial-sts2/releases/tag/v0.0.1
