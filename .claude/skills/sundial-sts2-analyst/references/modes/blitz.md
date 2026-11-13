# Blitz runs

Read this only when the run summary's header says Blitz ("Ironclad Blitz A0"). Blitz is a short, faster mode added
in v0.113 (beta). Analysing it is optional: most players treat Standard as the mode they're improving at, so keep a
Blitz report lighter than a Standard one and say so up front.

## What's different

- **Every act is the same 8 rooms:** Ancient, two hallway fights, merchant, elite, treasure, rest site, boss. 24
  floors, no map and no route choice. The elite is always the fifth floor of the act, with no rest site before it.
- **Each Ancient heals you to full** (seen at the start of Acts 2 and 3). HP left at the end of an act is refunded.
- **Gold stays at 99** and isn't spent. The merchant sells **services** instead: you take three of six (card removal,
  card rewards, rare or upgraded rare cards, a prismatic card reward from another character, upgrades, transforms,
  two more choices). A card choice at the merchant came from a service, so it counts as a card reward.
- **Act 1's Neow offers cards and you take three** (the floor log reads "took X, Y, Z over ...").
- **Its own ascension ladder,** shared by all characters. Enemy numbers in the summary are base values: Blitz levels
  aren't mapped to enemy stats.
- **Baselines** compare only with the player's other Blitz runs on that character. Most players have few: say when
  there's no baseline and judge the run on its own terms.

## What to judge

- **Neow:** which three cards were taken and whether they cover the first elite (F5) and the Act 1 boss (F8). Act 1
  is short, so front-loaded damage matters more than scaling that needs feeders.
- **Merchant services:** what was taken and passed (removals, rare rewards, upgrades), and what the deck needed at
  that point. `player_summary(mode="blitz")` shows which services the player usually takes.
- **The F5 elite and the boss:** HP and deck shape entering each, and whether the act's HP was spent where it bought
  something (elite rewards) given that the next Ancient refunds it.
- **Draft and deck shape** as usual: role counts, archetype states, picks that made or broke it.

## What not to judge

- Routing, elite counts, shop timing and gold: Blitz offers no choice there.
- Rest versus smith by Standard norms: with a full heal at the next Ancient, resting before a boss is cheap.
- Never compare a Blitz run with Standard runs, or Standard habits with Blitz ones.

## Report shape

Use the usual sections, shorter: about 250–400 words. Open with one line noting that Blitz analysis is lighter and
optional. Expert slots follow the per-slot notes from `get_enabled_experts(mode="blitz")`.
