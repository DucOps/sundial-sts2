# Sundial

*Every run leaves a shadow.* Sundial turns your Slay the Spire 2 run history into something you can actually
read: every run in one sortable list, the full floor-by-floor story of each one, and charts of how you're climbing.

> Unofficial fan project, not affiliated with or endorsed by Mega Crit. A weekend project, built with AI, to help
> me get better at the game. Provided as is, with no warranty (see [Licence](#licence)).

![Sundial overview: win rate, recent form, floor reached over time, what kills you](docs/images/overview.png)

<sub>Screenshots use generated demo data, not a real player's history.</sub>

## Why

I came to Slay the Spire late, and StS2 arrived just as I fell for it. Stuck on A10 Ironclad, I kept opening the
in-game run history and not finding what I wanted: which fights keep killing me, how long each ascension took,
what I picked and skipped, which patch a run was on. I play across a PC, a Steam Machine and an Ayn Thor, and
every run is saved locally as a file. Sundial reads those files and shows them the way I wanted to see them.

## What it does

**Run history and dashboard** (the main thing; no install, nothing uploaded):
- **Overview:** win rate, deaths by room and killer, activity over time, per character and ascension.
- **Runs:** every run in one sortable, filterable table. Open any run for its HP chart, path, deck, relics and a
  floor-by-floor log of picks, skips, rests, shops, potions and damage.
- **Climb:** how many attempts and days each ascension took, run by run.
- **Patches:** which early-access version each run was played on, with first clears per version.
- **Cards, Relics & Ancients, Fights:** pick rates, win rates and your damage against each encounter.
- Merge runs from several devices: re-import any time and only new runs are added.

| Runs | Run detail | Climb |
|---|---|---|
| [![All runs table](docs/images/runs.png)](docs/images/runs.png) | [![One run: HP by floor, path, deck and relics](docs/images/run-detail.png)](docs/images/run-detail.png) | [![Ascension climb](docs/images/climb.png)](docs/images/climb.png) |

**A permanent archive** (optional, with the Python package): the game prunes old runs, so the archive keeps a copy
of every run it sees.

**Post-game analysis** (optional, for fun): if you use Claude or another MCP client, Sundial's MCP server lets the AI
read a run and write up what decided it, using your own history as the baseline. You can add **experts**,
viewpoints you write yourself, for extra takes on each run. Skip this entirely if AI isn't your thing; nothing
else depends on it.

## Quick start: the dashboard

1. Open `web/dist/sundial-blank.html` in a browser.
2. Click **Import runs** and choose your runs: the `history` folder, a few `.run` files, or a zipped saves folder.
3. Runs are saved in that browser, so next time just open the page. Import again after new runs.

Where to find your runs:

| Device | Where |
|---|---|
| Windows PC | `%APPDATA%\SlayTheSpire2\steam\<SteamID>\profileN\saves\history` |
| Steam Cloud copy (Windows) | `C:\Program Files (x86)\Steam\userdata\<id>\2868840\remote\` |
| Steam Machine / Steam Deck / Linux | Not verified yet. Steam Cloud usually syncs these runs to your PC, so importing on the PC covers them. |
| Android handheld (e.g. Ayn Thor via GameNative) | Export the game's saves as a zip and import the zip. |

The game only keeps your recent runs in `history`, so import regularly (or use the archive below).

## Optional: archive and post-game analysis

Needs Python 3.11+ via [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`).

1. Put this folder somewhere permanent and run `uv sync`.
2. Connect the MCP server to your AI client.
   - **Claude Code** (VS Code or terminal): open this folder. `.mcp.json` registers the server and
     `.claude/skills/` holds the analysis skill; approve the server when asked.
   - **Claude Desktop:** Settings → Developer → Edit Config, then add:
     ```json
     {
       "mcpServers": {
         "sundial-sts2": {
           "command": "uv",
           "args": ["--directory", "C:\\path\\to\\sundial-sts2", "run", "sundial-sts2"]
         }
       }
     }
     ```
     Restart Claude Desktop, then zip `.claude/skills/sundial-sts2-analyst` and upload it in Claude's skills
     settings.
3. Ask: *"analyse my latest run"*, *"why did I die last run?"*, *"what patterns do my A10 deaths have?"*
4. To see analyses in the dashboard, import your `~/.sundial-sts2` folder. Each one appears at the bottom of its
   run, with a toggle for each expert section.

Optional card text, so the analysis knows what cards, relics and potions do and can count deck coverage:
`uv run --with dnfile python tools/import_game_data.py` reads it from your own game install (current patch,
with numbers and upgrades) into `~/.sundial-sts2/knowledge/game.json`. Pass the game folder if it isn't in the
default Steam location, and re-run it after a patch. Nothing is downloaded and no game data ships with Sundial.
The result is derived from the game's files on your machine, for your own use. It works by reading the game's
internal formats, which Mega Crit can change in any update, so it may break or produce wrong text after a patch;
future support isn't guaranteed. It uses [dnfile](https://github.com/malwarefrank/dnfile) (MIT) to read `sts2.dll`.
Older alternative (community data from v0.98): `git clone https://github.com/cjodo/sts2 %TEMP%\sts2-data`, then
`uv run python tools/import_community_data.py %TEMP%\sts2-data`.

### Archive settings

On every tool call the server copies new `.run` files from the game's save folder into
`~/.sundial-sts2/archive`, which is never pruned (the game only keeps your recent runs).

| Setting (env var) | Default |
|---|---|
| `STS2_SAVE_ROOT` | `%APPDATA%\SlayTheSpire2` (macOS `~/Library/Application Support/SlayTheSpire2`) |
| `STS2_EXTRA_DIRS` | none. Extra folders separated by `;`, e.g. an unzipped phone/GameNative export |
| `STS2_ARCHIVE` | `~/.sundial-sts2/archive` |
| `SUNDIAL_HOME` | `~/.sundial-sts2` (archive, experts, analyses, lessons, knowledge) |

Upgrading from the prototype (`~/.spire-ledger`)? On first start Sundial copies it to `~/.sundial-sts2` once and
leaves the old folder in place.

Set them in the `"env": { ... }` block of the Claude Desktop config.

### Experts (optional)

The core analysis is neutral and based on your own data. On top of it you can add **experts**: short cards you write,
each describing a point of view on how to play. Every enabled expert gets its own section in each analysis, and the
dashboard lets you toggle them or compare them side by side.

- Experts live in `~/.sundial-sts2/experts/<slug>/expert.md`. Three examples ship in `experts/`:
  `steady-hand` (survival first), `greedy-climber` (elites and relics) and `house-rules` (your own rulebook).
  Copy them over and enable one or two.
- Write your own from the [template](src/sundial_sts2/expert_template.md), or let AI help: pick the
  **write_expert** prompt in Claude Desktop, or paste the interview prompt from the guide into any AI chat.
- Ask Claude: *"list my experts"*, *"enable greedy-climber"*, *"help me write an expert"*.
- Full guide: [docs/creating-an-expert.md](docs/creating-an-expert.md).

### Character notes (what the analyst knows about the game)

The analysis skill reads [`characters.md`](.claude/skills/sundial-sts2-analyst/references/characters.md) on every
run. It's a plain-text guide to each character: starting kit, mechanics (Sly, orbs, Osty and Doom, Stars and
Forge), common archetypes, the cards that usually cover AoE, scaling, block and draw, and the usual ways runs fail.
It also notes fights that change what a deck needs, such as the Aeonglass boss.

**How it's used.** It gives the AI context to judge a deck by that character's own standards: a Necrobinder deck
isn't measured against Ironclad norms. It doesn't replace your data: verdicts still come from your own runs and
baselines, and card text from your run data or `lookup` always wins over the notes.

**How it was made.** In November 2026 an AI assistant compiled it from community guides and tier lists for Early
Access v0.107 to v0.111 (the sources are listed at the bottom of the file). Ironclad card names
were checked against real run files. Nothing else has been checked by hand yet, there's no official StS2 wiki to
check against, and the game is still changing, so expect some of it to be out of date or wrong.

**How to improve it.** It's a Markdown file, so edit it directly:
- Fix anything that doesn't match your games: wrong card effects, archetypes that don't work, failures it misses.
- Add what you learn as you play a character, in the same layout (Kit, Mechanics, Archetypes, Coverage, Typical
  failures), so the analyst can find it.
- Keep it factual and general. Your own rules for how to play (for example "never skip elites in Act 1") belong in
  an [expert card](#experts-optional), not here.
- Say when you're unsure. The analyst treats this file as context, not proof.
- After editing: Claude Code picks it up automatically. For Claude Desktop, zip the skill folder again and
  re-upload it.

Corrections are welcome as issues or pull requests.

### MCP tools

Runs: `list_runs`, `get_run_summary`, `get_floor`, `encounter_history`, `player_summary`, `ascension_climb`,
`version_summary`, `lookup`, `get_lessons`, `save_lesson`, `status`.
Experts: `list_experts`, `get_enabled_experts`, `set_expert_enabled`, `get_expert`, `create_expert`,
`list_expert_sources`, `read_expert_source`, `save_expert_card`.
Analyses: `save_analysis` (writes the analysis for the dashboard).
Prompts: `analyse_run`, `write_expert`, `build_expert`.

## Project layout

| Path | What it is |
|---|---|
| `web/` | The dashboard: `src/` (single-page app + JS parser), `build/`, `dist/sundial-blank.html` |
| `src/sundial_sts2/` | Python package: `.run` parser, archive, analysis, MCP server |
| `.claude/skills/sundial-sts2-analyst/` | The analysis skill |
| `experts/`, `docs/` | Example expert cards and the guide to writing your own |
| `examples/` | A sample post-game analysis |
| `tests/` | Smoke test and three fixture runs (`uv run python tests/smoke.py`) |
| `tools/import_game_data.py` | Optional: build card/relic/potion text from your own game install |
| `tools/import_community_data.py` | Optional: import older community card/relic/potion text for your own use |

## Troubleshooting

- **Windows on ARM:** if `uv sync` fails building a dependency, use x64 Python: `uv sync --python cpython-3.12-windows-x86_64-none`.
- **Claude doesn't see the tools:** check Claude Desktop's MCP logs (Settings → Developer) and that the path in `--directory` is right.
- `status` shows which folders are scanned, how many runs are archived, and which knowledge files loaded.

## Versions

Current version: **0.0.2**. See the [changelog](CHANGELOG.md) for what changed in each release; the
version is also shown in the dashboard footer.

## Licence

[MIT](LICENSE). The software is provided **"as is", without warranty of any kind**. Use it at your own risk. It only
reads your save files and never writes to them, but back up anything you care about.

**Disclaimer:** Sundial is an unofficial fan project made by a player to get better at the game. It is not
affiliated with, endorsed by or supported by Mega Crit. *Slay the Spire* and *Slay the Spire 2* are trademarks of
Mega Crit; all game names, content and data belong to their owners. No game assets or data are bundled: card and
relic text is imported locally by each user, either from community data or derived from the user's own copy of
the game. Those importers depend on formats outside this project's control and may stop working at any time.
