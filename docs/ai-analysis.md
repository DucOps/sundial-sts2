# The AI post-game analysis: a guide for tinkerers

Sundial is a run ledger first. The AI post-game analysis is a side experiment: how far can an AI get at explaining
a Slay the Spire 2 run if you give it the game's own facts and your own history, instead of letting it guess? This
guide explains how the experiment is built, what each part does and why, and how to change it for yourself:
archetypes, card annotations, character notes, experts and the report itself.

Nothing here is needed for the dashboard. If you don't use an AI client, you can ignore this whole page.

- [How it fits together](#how-it-fits-together)
- [Layer 1: game facts from your install](#layer-1-game-facts-from-your-install)
- [Layer 2: the knowledge layer (roles, mechanics, archetypes)](#layer-2-the-knowledge-layer)
- [Layer 3: the Sundial analyst](#layer-3-the-sundial-analyst)
- [Layer 4: experts](#layer-4-experts)
- [The run summary, section by section](#the-run-summary-section-by-section)
- [What gets saved, and where](#what-gets-saved-and-where)
- [Tinkering recipes](#tinkering-recipes)
- [Limits](#limits)
- [Contributing to the analysis](#contributing-to-the-analysis)
- [MCP tools](#mcp-tools)

## How it fits together

```
 your .run files ──► archive (~/.sundial-sts2/archive)
                          │
 your game install ──► game facts ─┐
 knowledge/ (YAML) ──► roles,      ├─► MCP server ──► run summary ──► AI client + analyst skill ──► report
   archetypes                      │   (computes the facts)            (writes the story)               │
 your history ──► baselines ───────┘                                                                     │
 your expert cards ──────────────────────────────────────────────────► expert slots ◄──────────────────┘
                                                                                     │
                                                         save_analysis ──► dashboard (analysis panel)
```

The split that matters: **the server computes facts, the AI writes the story.** Anything that can be counted
(HP, damage against your baseline, role counts, archetype states, enemy numbers at your ascension) is computed in
Python and handed to the AI as plain text it can cite. The AI's job is to find which of those facts decided the
run. That keeps the AI from inventing card effects or miscounting a deck, and it makes the analysis easy to inspect:
ask for `get_run_summary` yourself and you see exactly what the AI saw.

There are two kinds of opinion in a report, kept apart on purpose:
- **The Sundial analyst** describes. It uses game facts and your own baselines, the same way for every character.
- **Experts** prescribe. Each is a viewpoint you write (a playstyle, your own house rules) and gets its own section.

A useful test for where something belongs: if a statement could be right for one playstyle and wrong for another,
it's an expert's opinion, not a fact for the analyst.

## Layer 1: game facts from your install

On first start, and again after every game update, the server reads your own Slay the Spire 2 install and builds
`~/.sundial-sts2/knowledge/game/game-<version>.json`. Nothing is downloaded and nothing from the game ships with
Sundial. Text comes from the game's localisation files (`SlayTheSpire2.pck`); numbers come from reading the game's
code (`sts2.dll`, via [dnfile](https://github.com/malwarefrank/dnfile)), without running it.

| Kind | What you get |
|---|---|
| `card`, `relic`, `potion`, `enchantment` | Text with real numbers (and upgraded numbers), cost, type, rarity, owner, plus the mechanics each card feeds or pays off |
| `power`, `keyword`, `term` | What Vulnerable, Plating, Exhaust, Sly, Block, Channel... mean, in the game's words |
| `character` | Starting HP, gold, deck and relic |
| `monster` | HP and every move: its intents (attack, multi-attack, buff, debuff, status cards...), the powers it applies, the cards it adds, and its numbers, with ascension variants (e.g. "Ebb Damage 22 (26 from A9)") |
| `encounter`, `act` | Hallway / elite / boss, which monsters, which act; each act's bosses, Ancients and events |
| `event` | Each event's options with their numbers; Ancients |
| `ascension`, `orb` | What each ascension level changes; orb passive and Evoke text |

The official patch notes that ship with the game are saved next to it (`patch-notes.json`) and searchable with the
`patch_notes` tool.

Anything the reader can't evaluate is left out, never guessed: a monster whose HP depends on the fight shows "HP not
readable", a value computed in combat shows as X. Try it: ask your AI to `lookup` "Aeonglass", "Ironclad" or
"Abyssal Baths".

**Why from the game:** it's always the version you're playing, and it's the only source that can't be wrong about
what a card says. **The catch:** it reads internal formats Mega Crit can change in any patch, so a game update can
break it. If a build fails, the last good one keeps working and `status` says why.

## Layer 2: the knowledge layer

The game tells you what each card says. It doesn't tell you what the card is *for* in a deck, or which cards belong
together. The knowledge layer adds that, as descriptively as possible. Its spec is
[`knowledge/SCHEMA.md`](../knowledge/SCHEMA.md); this is the short version.

**Roles** (fixed list) say what a card contributes: `front_load`, `aoe`, `scaling`, `block`, `draw`, `energy`,
`debuff`, `sustain`, `card_gen`, `deck_thin`. They replace the old "deck coverage" keyword check. Tag what a card
does reliably, not on its best day: temporary Strength isn't `scaling`.

**Mechanics** are a character's vocabulary: Strength, Exhaust, Poison, Shivs, Sly/discard, Orbs, Doom, Osty, Stars,
Forge and so on. A card is an *enabler* of a mechanic (it makes it happen), a *payoff* (it rewards it) or *both*.

**Archetypes** are built on one mechanic each, never on hand-picked card lists. A deck's archetype state is
computed from its enablers (E) and payoffs (P):

| State | Means |
|---|---|
| `absent` | No cards for it |
| `forming` | Some pieces, not enough to call it a plan |
| `committed` | Enough enablers and payoffs (each archetype sets its own thresholds) |
| `half_built` | Payoffs bought without enough enablers to feed them: the flag worth reading |

Plus `support_ok` (does the deck have the roles the archetype needs, e.g. 2 draw for an Exhaust engine), the
**primary** archetype at each boss, the floor each one **committed**, **pivots** (the primary changed by a clear
margin), and **orphans** (cards whose only value is a mechanic nothing else in the deck uses).

Where the definitions come from, in order:
1. **Generated from game text, for every character.** Each mechanic the character's own cards both feed (3+ cards)
   and pay off (1+) becomes an archetype, committed at 2 enablers and 1 payoff. Card tags come from the game-data
   builder reading card text (`src/sundial_sts2/mechanics.py`).
2. **Hand-written, where someone has done the work:** `knowledge/<character>/archetypes.yaml` replaces a generated
   archetype built on the same mechanic (better name, tuned thresholds, support roles, keystones) and can add
   archetypes text can't find (Ironclad's Barricade / block).
3. **Card annotations** in `knowledge/<character>/cards.yaml` override what text tagging says about a card's roles
   and mechanics. Cards without one are counted from their text and marked `*` in the summary.

**Why this shape:** generated archetypes give every character coverage the day it's added to the game, with zero
upkeep. Hand-written YAML is only needed where text tagging gets something wrong or a player knows better, and it
stays small. Annotations carry a review status (`draft` / `reviewed`, by `ai` / `human`) and the game build they
were checked on. When a later build changes a card's text, the annotation is reported as **stale**, and the report's
Confidence section says how many draft, stale and unannotated cards it leaned on.

Current state: Ironclad and Silent have hand-written archetypes (Ironclad 23 annotated cards, all draft); Defect,
Necrobinder and Regent run on generated archetypes only.

## Layer 3: the Sundial analyst

The Sundial analyst is an AI skill: instructions in
[`.claude/skills/sundial-sts2-analyst/`](../.claude/skills/sundial-sts2-analyst/) that tell the AI how to read the
run summary and write the report.

| File | What it controls |
|---|---|
| `SKILL.md` | The workflow (which tools to call, in what order) and the rules (cite floors, your baselines decide what's bad, never invent card effects, read archetypes as facts) |
| `references/analysis-framework.md` | What to look at, in order: the ending, HP economy, deck shape at each boss, draft decisions, potions, patterns |
| `references/report-format.md` | The report's sections and length |
| `references/data-notes.md` | What each number in the summary means and its limits |
| `references/characters/<character>.md` | One short file per character (core resource, what counts as real scaling, how it covers AoE, block and draw, known gaps, a coverage status). Only the run character's file is loaded, plus `_shared.md` |

The report it writes: **Verdict**, **What ended it** (the final fight and the root cause, usually 10–20 floors
earlier), **Turning points**, **Deck & draft** (role counts and archetype facts), **HP, rests, gold & potions**,
**What went right**, **Lessons for next run**, and **Confidence** (what the data couldn't show, and which knowledge
was draft or stale).

It learns about you over time in two ways: your **baselines** (every comparison is against your own finished runs
on the same character and ascension) and **lessons** you agree to save (`save_lesson`), which it reads before each
analysis so it can say whether you kept them.

## Layer 4: experts

An expert is a short card you write: a persona with a playstyle, your own house rules, or your summary of a
guide. Each enabled expert gets its own section after the analyst's report, applying only its own principles
(each tagged with an ID such as SH2 so you can see which one it used). When two disagree, the report says where.
In the dashboard you can toggle experts on and off, or compare them side by side.

Three examples ship in [`experts/`](../experts/): `steady-hand` (survival first), `greedy-climber` (elites and
relics) and `house-rules` (a personal rulebook). The full guide to writing your own is
[creating-an-expert.md](creating-an-expert.md).

## The run summary, section by section

`get_run_summary` is what the AI reads first. Every section is computed by the server; the AI adds no numbers.

| Section | What it says | Comes from |
|---|---|---|
| Header | Character, ascension, result, version, seed; which runs the baselines use; the character's starting kit | Run file, your history, game facts |
| How it ended | Final room, HP going in, turns; your history against that fight; potions and gold left | Run file, your history |
| This run vs your baseline | Damage per act, elites, HP entering each boss, deck size, skip rate, removals, potions, rest vs smith | Your finished runs on the same character and ascension |
| Fights well above your usual damage | Fights that cost 1.5× your average (and 10+ HP) | Your history |
| Enemies in the deciding fights | For the killer, the bosses and those fights: HP and each move's intents, powers, status cards and numbers at the run's ascension | Game facts |
| Deck roles and archetypes at each boss | Role counts, each archetype's state with E/P counts and support, cards passed that would have covered a missing role | Knowledge layer |
| Archetype timeline | Where definitions came from, primary archetype per boss, commit floors, pivots, half-built archetypes, orphans | Knowledge layer |
| Knowledge confidence | How many of the cards involved were annotated, draft, stale or counted from text | Knowledge layer |
| Synergies | Per mechanic, what feeds it and what pays it off, with warnings (e.g. self-damage with no payoff) | Card text tags |
| Deck at each boss, final deck | The reconstructed decks, relics (with floor found) and potions | Run file |
| Floor log | One line per floor: room, fight, HP change, picks and skips, rests, shops, events | Run file |
| What things do | Text of every card, relic, potion, event and keyword involved | Game facts |

`get_deck_snapshots` shows the same roles and archetype states at every card reward and shop, for "when did the
plan form, stall or change?".

## What gets saved, and where

Everything lives in `~/.sundial-sts2/` (set `SUNDIAL_HOME` to move it):

| Path | What |
|---|---|
| `archive/` | Every run the server has seen; never pruned. A file that cannot be read is reported by `status` (`runs_unreadable`), never dropped silently |
| `knowledge/game/` | Game facts per game version, `current.json`, `patch-notes.json` |
| `knowledge/*.json` | Your own extra knowledge files (optional; same format as game facts, they override them) |
| `experts/<slug>/expert.md` | Your expert cards (and a `sources/` folder for your notes) |
| `config.json` | Which experts are enabled, in slot order |
| `lessons.json` | Lessons you chose to save |
| `analyses/<run id>.json` | Saved analyses for the dashboard |

A saved analysis is JSON with `type: "sundial-sts2-analysis"`, the run it belongs to, `core` (the Sundial analyst's
verdict and markdown; the field kept its original name so older files still load), `experts` (one entry per slot:
slug, name, kind, verdict, markdown) and `experts_differ`. Import the folder in the dashboard to see them.

## Tinkering recipes

Edits to `knowledge/` are picked up on the next run summary. Edits to the skill are picked up by Claude Code
straight away; for Claude Desktop, zip `.claude/skills/sundial-sts2-analyst` again and re-upload it. Edits to
Python need a server restart. After any `knowledge/` edit, run:

```
uv run python knowledge/scripts/validate_knowledge.py knowledge
```

Add `--card-ids <file>` to also check card ids exist (make the file with
`uv run python knowledge/scripts/game_card_ids.py > ids.txt`; it's built from your game, so don't commit it).

### Correct a card the text tagging gets wrong

Card ids are the game's ids in lower case (`lookup` shows the name; the id is the name in `UPPER_SNAKE` case). In
`knowledge/<character>/cards.yaml`:

```yaml
  - id: burning_pact
    roles: [deck_thin]                       # from the fixed role list
    mechanics: [{ tag: exhaust, as: enabler }]   # tag must be a mechanic in that character's archetypes.yaml
    upgrade_impact: high
    notes: Exhausts 1 card, draws 2 (3 upgraded); net card advantage only once upgraded.
    review: { status: draft, build: v0.111.0, by: human }
```

Set `review.status: reviewed` once you're confident, and `build` to the game version you checked against.

### Rename, tune or add an archetype

In `knowledge/<character>/archetypes.yaml`. An archetype with the same `mechanic` as a generated one replaces it:

```yaml
schema_version: 1
character: defect
keystone_weight: 2
mechanics:
  - tag: orbs
    description: Channels orbs (enabler), or gains from Focus, Evoke or orb count (payoff).
archetypes:
  - id: orbs
    name: Orb engine
    mechanic: orbs
    keystones: []                 # cards that commit a deck on their own (must be payoffs)
    thresholds:
      committed: { enablers: 3, payoffs: 2 }
    support: { draw: 1 }          # roles the plan needs, with minimum counts
    notes: Descriptive only: what the engine does and what it's weak to. No "you should".
```

A character folder needs a `cards.yaml` too (it can be `cards: []`). To add a mechanic the text tagging doesn't know
at all, either tag cards with it in `cards.yaml`, or add a text rule to `src/sundial_sts2/mechanics.py` (and bump
`BUILDER_VERSION` in `gamedata.py` so your game facts are rebuilt). The rules for generated archetypes
(3 enablers, 1 payoff, committed at E2 P1) are constants at the top of `src/sundial_sts2/annotations.py`.

### Edit character notes

`.claude/skills/sundial-sts2-analyst/references/characters/<character>.md`. Keep them factual and short: the core
resource, what counts as real scaling, how the character usually covers AoE, block and draw, known gaps. Update the
coverage status line when you've checked a character. Your opinions on how to play go in an expert.

### Write or change an expert

Ask the AI *"help me write an expert"* (it interviews you, drafts the card and saves it when you approve), or copy
the [template](../src/sundial_sts2/expert_template.md) into `~/.sundial-sts2/experts/<slug>/expert.md`. A card has
frontmatter (`name`, `slug`, `description`, `kind: persona | personal | community`, `characters`, `version`, `sources`)
and sections: Who this is, Core principles (ID-tagged, specific enough to judge a run), What to look for in a run,
Character notes, How it should read, Limits, Sources. Then *"enable <slug>"*. Details in
[creating-an-expert.md](creating-an-expert.md).

### Change the report

Section order and length: `references/report-format.md`. What the analyst looks at and in which order:
`references/analysis-framework.md`. Rules it must follow: `SKILL.md`. Keep expert slots separate from the analyst's
own sections; the dashboard relies on that split.

### Add your own facts

Drop a JSON list into `~/.sundial-sts2/knowledge/` with entries like
`{"id": "MY_NOTE", "kind": "term", "name": "...", "text": "..."}`. Later files override earlier ones, so this is
also how you'd correct a game-fact entry the builder got wrong.

## Limits

- **No combat log.** Run files record cards, relics, HP, damage per floor and turns, not what was drawn or played.
  Orbs, Stars, Forge, Osty's HP, Poison and Doom amounts aren't recorded; the analyst infers the engine from the deck
  and says so.
- **Decks are reconstructed.** The deck at a boss is rebuilt from the final deck plus removals and transforms;
  upgrades are shown as of the end of the run.
- **Monster moves have no order.** The summary shows what each move does, not how often or in what sequence.
- **Thresholds are guesses.** Archetype thresholds and support minimums haven't been tuned against many runs yet.
- **It's an AI.** It can still misread a summary. Every claim should cite a floor; check the ones that matter.

## Contributing to the analysis

Sundial is open source, and contributions are welcome, especially from players who
understand the game's mechanics better than I do. If you can translate that into
better analysis, I'd love the help.

**The Sundial analyst vs experts.** The Sundial analyst should *describe* the game: what a
card does, which cards feed which mechanics, and what an encounter punishes. It
shouldn't *prescribe* a way to play. A useful test: if a statement could be right
for one playstyle and wrong for another, it belongs in an expert card, not the analyst.
Experts are personal viewpoints that users write and enable themselves.

**Good contributions**
- Reviewed card annotations in `knowledge/<character>/cards.yaml`, especially for
  characters you main (set `review.by: human` and the game build you checked)
- Mechanics and archetype definitions for characters that are still thin
- Improvements to the analyst skill's framework, or to the character notes in
  `.claude/skills/sundial-sts2-analyst/references/characters/<character>.md`
- Golden runs: a run plus a short note on what actually decided it, so changes
  can be tested against real outcomes

**Guidelines**
- Back claims with card text, game data or run data, and say when something is
  inference.
- Write in your own words. Credit community sources you drew on, but don't copy
  guides or present them as an author's own views.
- Run `uv run python knowledge/scripts/validate_knowledge.py knowledge` before opening a PR.
- Note the game build. The game is in early access, and text changes between patches.

## MCP tools

| Group | Tools |
|---|---|
| Runs | `list_runs`, `get_run_summary`, `get_deck_snapshots`, `get_floor`, `encounter_history`, `player_summary`, `card_history`, `ascension_climb`, `version_summary` |
| Game facts | `lookup`, `patch_notes`, `status` |
| Lessons | `get_lessons`, `save_lesson` |
| Experts | `list_experts`, `get_enabled_experts`, `set_expert_enabled`, `get_expert`, `create_expert`, `list_expert_sources`, `read_expert_source`, `save_expert_card` |
| Analyses | `save_analysis` (writes the analysis for the dashboard) |
| Prompts | `analyse_run`, `write_expert`, `build_expert` |
