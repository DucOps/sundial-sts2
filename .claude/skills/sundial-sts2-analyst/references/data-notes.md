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
- **Baselines** compare with the player's other finished runs on the same character, game mode and ascension
  (widened to ±1 ascension when there are fewer than 12). "In runs that cleared act N" uses only runs that beat that act.
  When the header says there is no baseline yet, the "typical" column is empty: describe the run on its own terms.
- **Game modes** (v0.113+, beta): Standard, Daily, **Blitz** and **Dread** (every ascension modifier on, bosses
  stronger and buffing their act, curses pile up). The header shows the mode when it isn't Standard ("Blitz A3").
  Blitz is a short mode with its own ascension ladder: every act is the same 8 rooms (Ancient, two hallway fights,
  merchant, elite, treasure, rest, boss), 24 floors in all, and Gold stays at 99. Act 1's Neow offers cards and you
  take three ("took X, Y, Z over ..."). The merchant sells services instead of stock: you take three of six
  ("merchant: took Card Removal, Random Upgrades, Card Rewards over ..."), and a card choice there came from a
  service, so it counts as a card reward. Custom games are labelled "Custom A7" and only compared with each other.
  Runs are only ever compared within one mode; `player_summary`, `encounter_history` and `ascension_climb` default
  to Standard and take `mode`. Blitz enemy numbers are shown at base values (its ladder isn't mapped to enemy stats),
  Dread's at A10 plus the boss HP bonus some bosses get in Dread; other Dread bonuses to boss moves aren't shown.
  For Blitz runs, `references/modes/blitz.md` says what to judge and what not to. Never hold a Blitz run to Standard norms for floors, gold or deck size.
- **Encounter history** covers all ascensions for that character and mode unless a level is given. Treat n < 5 as anecdotal.
- **Not recorded:** turn-by-turn combat, cards drawn or played, enemy intents, and the map routes not taken.
- **Game data** (card, relic, potion, power and keyword text) is normally built from the player's own game install
  for the installed version (`status` → `game_knowledge` shows which). Values that depend on the fight show as X.
  If `status` reports a failed build or an older version than the run, say the text may be out of date. An older
  community list (v0.98, "[icon amount missing]") may be loaded instead on some setups.
- **Enemies in the deciding fights** come from the game files: HP and each move's intents, powers, status cards and
  numbers at the run's ascension. They don't show the order or frequency of moves, and some values aren't readable
  (shown as missing, never guessed). Use them to say what the fight demanded (e.g. multi-hits, Strength ramp, status
  cards), not what happened turn by turn.
- **Synergies section** lists, per mechanic, the deck's "feeds" (cards/relics that make it happen) and "payoffs"
  (that reward it), tagged from card text. Warnings flag self-damage, discard, Stars or Sadness fed with nothing rewarding
  them, payoff cards with little feeding them, and payoff cards passed as rewards. They're hints from wording:
  check the cards with `lookup` before building an argument on one.
- **Role counts** come from card annotations in `knowledge/<character>/cards.yaml` (what a card reliably does:
  front-load, AoE, scaling, block, draw, energy, debuff, sustain, card gen, deck thin). Cards without an annotation
  fall back to a keyword heuristic over their text and are marked `*`; that heuristic can miscount temporary
  effects as scaling, and cards with no text on file aren't counted. Strikes, Defends and curses are excluded.
- **Archetype states** are computed per deck by the server from `knowledge/<character>/archetypes.yaml`: E =
  enabler cards, P = payoff cards (a keystone counts extra), duplicates count, upgrades don't. `absent` (nothing),
  `forming`, `committed` (E and P at the archetype's thresholds), `half_built` (enough payoffs, too few enablers).
  `support ok` means every support role meets its minimum. Unannotated cards count toward E/P through their text
  tags; the summary says how many did. Thresholds are first guesses, not tuned yet.
- **Timeline facts:** commit floor = the first floor an archetype was committed (after that floor's picks);
  pivots = floors where the primary archetype (the committed one with the highest E+P) changed; orphans = annotated
  cards at the last boss whose only value is a mechanic nothing else in the deck uses.
- **Knowledge confidence:** draft = annotation not reviewed by a human; stale = reviewed on an older build and the
  card's text has changed since; not checked = no review build or no game data for it; unannotated = counted
  from text. Snapshots inherit the deck reconstruction's limits (upgrades as of run end).
- **Habit stats** in `player_summary` include Act 1 and Act 2 boss clear rates with and without AoE and draw in the
  deck. Use them to say whether a framework rule actually predicts this player's results.
