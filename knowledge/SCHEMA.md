# Sundial knowledge layer — schema v1

The knowledge layer gives the core analysis a **descriptive** understanding of the game: what each card is
for, which cards feed which mechanics, and when a deck counts as committed to a plan. It never says how the game
*should* be played; that belongs to experts. Rule of thumb: if a statement could be wrong for one playstyle and right
for another, it is an expert opinion, not knowledge.

```
knowledge/
  SCHEMA.md                          ← this file
  schema/
    cards.schema.json                ← validates <character>/cards.yaml
    archetypes.schema.json           ← validates <character>/archetypes.yaml
  ironclad/
    cards.yaml                       ← role/mechanic annotations per card
    archetypes.yaml                  ← mechanic vocabulary + archetype definitions
  silent/ … defect/ … necrobinder/ … regent/
  colorless/cards.yaml               ← shared cards (no archetypes file)
```

Card **text, cost, rarity and type are not duplicated here**. They come from the game data Sundial already
loads. Annotations reference cards by the same `id` and only add meaning.

---

## 1. Card annotations (`<character>/cards.yaml`)

| Field | Required | Meaning |
|---|---|---|
| `id` | ✓ | Card id as used in Sundial's game data. |
| `roles` | ✓ | What the card contributes to a deck, from the fixed role list below. Can be empty (`[]`). |
| `scaling_kind` | when `scaling` in roles | What it scales: `strength`, `dexterity`, `poison`, `doom`, `focus`, `orbs`, `stars`, `forge`, `block_retention`, `card_advantage`, `other`. |
| `mechanics` | | Links to mechanics from this character's `archetypes.yaml`, each with `as: enabler`, `payoff` or `both`. |
| `upgrade_impact` | | `low` / `medium` / `high`: how much the upgrade changes the card. Feeds "key card left un-upgraded" checks. |
| `notes` | | One line on anything the role tags can't express (conditional, temporary, clunky). |
| `review` | ✓ | `status` (`draft` / `reviewed`), `build` (game build the text was checked against), `by` (`ai` / `human`). |

**Roles (fixed list; change it only with a schema version bump):**

| Role | Tag it when the card… |
|---|---|
| `front_load` | deals meaningful damage on the turn it's played (kills Act 1 elites before they scale) |
| `aoe` | hits all enemies, or reliably spreads to multiple |
| `scaling` | makes later turns stronger than earlier ones, and the effect lasts the fight |
| `block` | blocks enough to matter against an Act 2+ attack |
| `draw` | gives net card advantage |
| `energy` | gives net energy |
| `debuff` | applies Weak, Vulnerable or similar to enemies |
| `sustain` | heals or gains Max HP |
| `card_gen` | adds cards to hand/draw pile |
| `deck_thin` | exhausts or removes *other* cards on purpose |

Tag what the card does reliably, not on its best day. A temporary Strength gain is not `scaling`; put it in
`notes` instead. This is where the old keyword heuristic went wrong.

## 2. Mechanics and archetypes (`<character>/archetypes.yaml`)

**Mechanics** are the character's own vocabulary (`exhaust`, `self_damage`, `strength`, `block_retention` …). Every
`mechanics[].tag` in `cards.yaml` must be listed here (the validator script checks this; JSON Schema can't
across files).

**Archetypes** are defined by mechanics, never by hand-maintained card lists. Membership is derived:
*enablers of archetype X = cards whose `mechanics` include X's mechanic with `as: enabler` or `both`*. One source of
truth per card, so re-tagging a card after a patch updates every archetype automatically.

| Field | Meaning |
|---|---|
| `id`, `name` | Identifier and display name. |
| `mechanic` | The mechanic this archetype is built on. |
| `keystones` | Cards that commit the deck on their own (count as `keystone_weight` payoffs). |
| `thresholds` | `committed: {enablers, payoffs}`. `forming` is anything above zero but below this. |
| `support` | Roles the archetype needs to function, with minimum counts (e.g. `draw: 2`). |
| `notes` | Descriptive only: what the engine does and what it's weak to. No "you should". |

## 3. Detection (computed in the MCP server, not by the model)

For each deck snapshot (every card reward, shop, and each boss), per archetype:

1. Count `E` = enabler cards, `P` = payoff cards (+ `keystone_weight − 1` for each keystone). Cards tagged `both` count once on
   each side. Duplicates count. Upgrades don't change counts.
2. State:
   - `absent`: `E = 0` and `P = 0`
   - `committed`: `E ≥ thresholds.committed.enablers` and `P ≥ thresholds.committed.payoffs`
   - `half_built`: `P ≥ thresholds.committed.payoffs` but `E` below threshold (**the important flag**: payoffs bought with nothing to fuel them)
   - `forming`: anything else
3. `support_ok`: every role in `support` meets its minimum in the same deck.

Per run, emit:

- `primary_archetype`: committed archetype with the highest `E + P` at each boss (or `none`).
- `commit_floor`: first floor each archetype reached `committed`.
- `pivots`: floors where `primary_archetype` changed.
- `half_built_at`: bosses where any archetype was `half_built`, or `committed` with `support_ok = false`.
- `orphans`: cards at the final boss whose only value is a mechanic no archetype in the deck uses, and whose
  roles add nothing the deck lacks.
- `role_counts`: per snapshot, the count of each role (replaces the current keyword "Deck coverage").

The analyst skill reads these as facts: "Exhaust committed on F18; at the Act 2 boss it was committed but had
1 draw card against a support minimum of 2."

## 4. Versioning and staleness

- `schema_version` at the top of each file. Bump it when roles or fields change meaning.
- Each card has `review.build`. When Sundial sees a run on a newer build than a card's `review.build` and that card's
  text differs in the game data, the card is reported as **stale** and its annotations are used with a caveat in
  the Confidence section.
- `review.status: draft` annotations are used but counted; if a report relies on more than ~3 draft cards, say so.

## 5. Authoring workflow

1. Script: for every card in game data with no annotation, ask the model for a draft entry
   (`review: {status: draft, by: ai}`) from the card text, using this file as the rubric.
2. Review in batches by character; flip to `reviewed`, `by: human`.
3. Run `validate_knowledge` (JSON Schema + cross-file checks: unknown mechanic tags, unknown card ids, keystones
   that aren't payoffs).
4. Re-run golden-run evals to confirm reports improved.
