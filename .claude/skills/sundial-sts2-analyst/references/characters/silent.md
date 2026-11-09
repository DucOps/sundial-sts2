# Silent

**Coverage status: partial.** The player is climbing ascensions on Silent now, so baselines are still building.
Archetypes are drafted in `knowledge/silent/archetypes.yaml` with low first-guess thresholds; no cards are annotated
yet, so every role count and archetype state comes from card text (marked *).

## Kit and core resource

70 HP. Ring of the Snake: draw 2 extra cards at the start of each combat. Starts with 5 Strike, 5 Defend,
Neutralize (3 damage, 1 Weak), Survivor (8 Block, discard 1 card).

Silent's resource is **cards in hand**: extra draw, discard and 0-cost cards. Lower HP than Ironclad, with no
healing from the starter relic, so damage taken matters more.

## Mechanics

- **Sly:** a Sly card discarded from hand before the end of the turn is played for free. Discard effects
  (Survivor and others) turn Sly cards into extra plays.
- **Poison:** poisoned creatures lose HP at the start of their turn; Poison drops by 1 each turn. Ignores block.
- **Shivs:** Shiv is a token attack (4 damage, Exhaust) that other cards add to the hand.
- **Weak** reduces incoming attack damage; Neutralize and others apply it.

## What counts as real scaling

Poison that keeps being applied or is triggered extra times (Accelerant); effects that improve every Shiv for the
fight (Accuracy, Infinite Blades); powers that pay off discards each turn.

## How it typically covers the basics

- **AoE:** Noxious Fumes, Bouncing Flask (random targets), Dagger Spray, Haze.
- **Block:** Survivor, Cloak and Dagger; Weak cuts incoming damage.
- **Draw:** Ring of the Snake, Acrobatics, Reflex, Adrenaline.

## Archetypes

Defined in `knowledge/silent/archetypes.yaml` (draft; the run summary reports their states): Poison, Shivs,
Sly / discard. Payoff cards are rare in all three, so `forming` is common; read the E/P counts, not only the state.
Describe what the deck contains; don't call one archetype stronger than another. Exhaust and Weak are also tracked, generated from game text.

## Known gaps

- No card annotations; everything is from card text, and the text tags have known misses (e.g. Well-Laid Plans
  counts as a discard enabler, Fan of Knives isn't counted as a Shiv payoff).
- Thresholds are low first guesses and have no support minimums; low confidence until ~15–20 Silent runs.
- Few runs: say when baselines are thin.
