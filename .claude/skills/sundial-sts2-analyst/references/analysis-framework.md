# Analysis framework

Work through these in order. Stop digging into an area once it's clearly not where the run was decided.
General principles below come from Slay the Spire 1 experience and broadly hold in StS2, but the player's own
baselines in the run summary outrank them.

## 1. The ending

- Where did it end: hallway, elite, boss, event? Deaths to hallway fights usually mean HP was already too low or
  the deck had no answer to a specific enemy. Elite deaths usually mean a greedy path or weak front-loaded damage.
  Boss deaths usually mean missing scaling, missing block, or low entry HP.
- **Entry HP vs the fight's history.** Compare HP entering the final fight with the player's average and worst
  damage against that encounter (`encounter_history`). If entry HP was below their *average* damage there, the run
  was lost before the fight began: look earlier.
- **Unused resources at death.** Potions held at death and gold unspent are free value that was never converted.
  Gold above ~300 at a death in Act 2–3 is a strong signal of a missed shop or no shop on the path.

## 2. HP economy (the most common root cause)

- Trace HP across the act. Find the floor where HP dropped and never recovered, and what caused it
  (an elite taken at low HP, an event that cost HP, a hallway fight far above average).
- **Rest-site choices.** Every rest at a rest site is an upgrade not taken. Resting is right when the next fights
  could kill you; it's a loss when HP is fine for what's ahead. Repeated forced rests (HP under ~40%) mean the
  damage problem was upstream: name it.
- **Elites.** Elites give relics, so taking them is good *when the deck can beat them cheaply*. Compare elites fought
  with the player's typical count for runs that cleared the act, and the damage taken in each with their history.
  Several elites each costing 30+ HP in Act 1 means the deck wasn't ready for that path.
- Burning Blood and similar heals are in the "+N" numbers; don't count them as rest decisions.

## 3. Deck shape at each boss

Use the reconstructed deck at each boss, the "Deck coverage" section (AoE, scaling, block, draw counted from card
text, plus reward cards passed that would have covered a gap), the "Synergies" section (what feeds what, and payoffs
passed) and the final deck. Unfamiliar keywords and powers are explained under "Keywords & powers" in the glossary.

- **Front-loaded damage for Act 1** (killing elites before they scale), **AoE** for multi-enemy fights,
  **scaling** (Strength, powers, exhaust engines) for bosses and Act 3, **block that keeps up** with Act 2–3 damage.
- **Deck size and basics.** Compare with the player's typical size and number of Strikes/Defends at that boss.
  Many basics late means few removals; a large deck with few upgrades means diluted draws.
- **Coherence.** Does the deck have a plan (e.g. self-damage + Rupture/Inferno, exhaust + Feel No Pain, Strength
  scaling, block + Barricade)? Count the cards that support it. Flag expensive cards picked late that the deck
  can't support (e.g. a 3-cost power with little block or draw).
- **Upgrades.** Count upgraded cards and which ones. Key attacks or powers left un-upgraded while rest sites were
  spent resting is a classic leak.

## 4. Draft decisions

- Card rewards: what was taken vs what was offered, especially at elites and bosses where offers are strongest.
  Point out the 1–3 picks that mattered most, in either direction. Don't relitigate every common.
- Skip rate vs their baseline. Taking a card at every reward bloats the deck; skipping too much leaves it weak.
- Ancient choices at the start of each act are big decisions. Compare the options when their text is known.
- Shops: what was bought, whether a removal was bought, and gold left afterwards.

## 5. Potions

- Potions drunk vs their baseline. Potions held at death were wasted.
- Using a strong potion in a hallway fight then dying to an elite/boss without one is worth noting.

## 6. Patterns (use `player_summary` and `get_lessons`)

- If something in this run also appears across many runs (e.g. rests far more than smiths, never takes a strong
  common card, dies holding potions), call it a habit and quantify it. Habits are the most useful lessons.

## Judging a win

For wins, the questions are: what made this run work that their losses lack, and where did it nearly fail?
Compare boss entry HP, upgrades, relics and deck shape with their baselines.
