# Ironclad

**Coverage status: partial.** The player's most-played character; most of the run history is Ironclad. Archetypes
are defined in `knowledge/ironclad/archetypes.yaml`; card annotations are still draft (23 cards, checked against
v0.111.0 text).

## Kit and core resource

80 HP. Burning Blood: heal 6 HP at the end of each combat. Starts with 5 Strike, 4 Defend, Bash (8 damage, 2
Vulnerable).

Ironclad has no second resource. Its resource is **HP**: Burning Blood refunds some of it after every fight, so HP
spent in a fight (self-damage, damage taken to race an elite) costs less than for other characters. Count that in
when reading damage-taken baselines, and remember high "−N" floors in a self-damage deck are partly self-inflicted.

## What counts as real scaling

Effects that last the whole fight and grow it:
- **Strength** gained for the fight (Inflame, Demon Form each turn, Rupture on HP loss). Multi-hit attacks gain most
  from it (Twin Strike, Sword Boomerang, Whirlwind, Conflagration). Strength "this turn" only is not scaling.
- **Exhaust payoffs** that trigger every time a card exhausts (Feel No Pain, Dark Embrace).
- **Self-damage payoffs** that trigger on each HP loss (Rupture, Inferno).
- **Block that stays** (Barricade, Plating from Stone Armor) with cards that build or convert it (Unmovable,
  Body Slam, Juggernaut).

## How it typically covers the basics

- **AoE:** Thunderclap, Breakthrough, Whirlwind, Conflagration, Inferno, Howl From Beyond.
- **Block:** Shrug It Off, Flame Barrier, Impervious, True Grit, Feel No Pain, Stone Armor; Barricade keeps it.
- **Draw / energy:** Battle Trance, Burning Pact, Pommel Strike, Shrug It Off, Dark Embrace; Bloodletting for energy.
- **Debuffs:** Vulnerable from Bash, Thunderclap and others.

## Archetypes

Defined in `knowledge/ironclad/archetypes.yaml` (source of truth; the run summary reports their states):
Strength scaling, Exhaust engine, Self-damage, Barricade / block. Don't restate thresholds here; cite the summary.

## Known gaps

- Card annotations cover 23 cards, all draft. Most deck cards are still counted from their text (marked * in the
  summary).
- Thresholds and support minimums are first guesses, not tuned against the player's runs yet.
- Other packages seen in runs (Vulnerable payoffs such as Molten Fist, Strike payoffs such as Perfected Strike)
  have no archetype definition.
