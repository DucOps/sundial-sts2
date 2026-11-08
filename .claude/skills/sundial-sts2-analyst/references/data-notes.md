# What the numbers mean

- **Floors** are counted across the whole run, starting at 1 with the Act 1 Ancient. Each act opens with an Ancient
  (A) that offers a choice of boons and refills HP. At A10 Act 3 ends with two boss fights in a row.
- **−N** on a floor is all HP lost there, including self-damage from the player's own cards (Bloodletting, Brand,
  Blood Wall, Inferno) and event costs. A high number in a self-damage deck isn't purely enemy damage.
- **(+N)** after HP is healing on that floor, mostly end-of-combat relic heals (Burning Blood +6, Meat on the Bone).
  Rest-site healing is shown in the rest line itself.
- **HP entering a fight** = HP after the floor + damage taken − healed. Approximate when a relic heals mid-fight.
- **Event fights** are "? event→fight X" lines: an unknown room that turned into combat.
- **Shops**: "other cards in stock" are not skipped rewards. Card-reward skip rates exclude shops.
- **Deck at each boss** is reconstructed from the final deck plus removals and transforms. Cards' upgrade state
  is shown as of the end of the run, not at that boss.
- **Baselines** compare with the player's other finished runs on the same character and ascension
  (widened to ±1 ascension when there are fewer than 12). "In runs that cleared act N" uses only runs that beat that act.
- **Encounter history** covers all ascensions for that character unless a level is given. Treat n < 5 as anecdotal.
- **Not recorded:** turn-by-turn combat, cards drawn or played, enemy intents, and the map routes not taken.
- **Game data** (card/relic text) comes from a community list dated around v0.98 and may be outdated; numbers
  shown as icons in game are sometimes missing ("[icon amount missing]").
- **Deck coverage counts** (AoE, scaling, block, draw) are a keyword heuristic over card text (e.g. "ALL enemies" = AoE, "Draw" = draw,
  Powers and Strength/Poison/Doom/Forge = scaling). Strikes and Defends are excluded. Temporary effects can be
  miscounted as scaling, and cards with no text on file aren't counted at all. Check a card before relying on it.
- **Habit stats** in `player_summary` include Act 1 and Act 2 boss clear rates with and without AoE and draw in the
  deck. Use them to say whether a framework rule actually predicts this player's results.
