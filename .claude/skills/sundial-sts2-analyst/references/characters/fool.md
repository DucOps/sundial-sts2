# The Fool

**Coverage status: draft, one run played.** New in v0.113 (beta branch only). Descriptive only, from game text.
Archetypes are generated from game text and no cards are annotated; the run summary's roles come from card text.
Mega Crit expects many changes before the Fool reaches the main branch: check `status` for the game version.

## Kit and core resource

77 HP, 99 Gold. Starting deck: 5 Strikes, 4 Defends, Foolish Shot. Song Bow: start each combat with 6 Aim.

Core resource: **Arrows**. Shots ("Shoot an Arrow to deal N damage") Impale the enemy; the Arrow is Dislodged after
you hit that enemy 3 times. **Aim** makes the next Arrow deal more damage. Several cards check "if the enemy is
Impaled" or reward Dislodging.

## Mechanics

- **Melodies:** playing a card with "Wah", "Cho" or "Ki" in its name gains that Melody for the turn. Payoffs check
  for a Melody, count them, or trigger on gaining one (or all three).
- **Sadness** is an unplayable Retain card that several cards add to your hand; payoffs trigger on creating it,
  count it, exhaust it, or transform it into **Joy** (gain 1 Energy, draw 1, Exhaust).
- **Stretch:** the next time you gain Block from a card, gain additional Block.

## What counts as real scaling

Aim that keeps coming (Archery, Whittling Knife, Storyteller) and Honing-style Arrow damage; Strength from Fertilizer.
Aim gained once and spent on the next Shot is closer to front-load.

## Archetypes

Generated from game text (the run summary lists and tracks them): Arrows, Melodies, Sadness, and others the deck
feeds. A mechanic counts when the character's own cards both feed it and pay it off. No hand-written
`knowledge/fool/archetypes.yaml` yet.

## Known gaps

Everything. Run data doesn't show Arrows, Aim, Melodies or Stretch during a fight; infer from the deck and say so.
