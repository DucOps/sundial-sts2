"""Game mechanics as enabler/payoff pairs, read from card and relic text.

Each mechanic has two rules:
  enables  - the card or relic makes the mechanic happen (loses HP, exhausts a card, applies Vulnerable, ...)
  rewards  - the card or relic pays off when it happens (Rupture, Feel No Pain, Cruelty, ...)

The game-data builder tags every entry with both lists; the run digest then checks each deck: lots of enablers
with no payoff (or a payoff with nothing feeding it) is a common way decks underperform. The rules match the
game's own wording, so they work for every character; they are heuristics, so treat the tags as hints.
"""
from __future__ import annotations

import re

# key: (label, enables regex, rewards regex). Patterns run on the card's text (including its upgraded text).
MECHANICS: dict[str, tuple[str, str | None, str | None]] = {
    "self_damage": ("Self-damage (HP loss)",
                    r"\b[Ll]ose \d+ HP\b",
                    r"[Ww]henever you lose HP|time you lost HP|for each time you lost HP"),
    "exhaust": ("Exhaust",
                r"(?<!you )\bExhaust\b(?! Pile)",
                r"[Ww]henever a card is Exhausted|[Ww]henever you Exhaust|times you Exhaust|in your Exhaust Pile"
                r"|this card is Exhausted"),
    "vulnerable": ("Vulnerable",
                   r"\b[Aa]pply \d+ Vulnerable|Vulnerable to ALL|Weak and Vulnerable",
                   r"Vulnerable enem|for each Vulnerable|enemy's Vulnerable"),
    "weak": ("Weak",
             r"\b[Aa]pply \d+ Weak|Weak and Vulnerable",
             r"Weak enem|for each Weak"),
    "strength": ("Strength",
                 r"\b[Gg]ain \d+ Strength(?! this turn)(?!\. At the end of your turn, lose)",
                 r"damage[^.]*?(twice|\d+ times|X times)|Strength affects|for each Strength"),
    "strike": ("Strike cards",
               None,                               # enabled by the card's name (see tag_entry)
               r"containing [“\"]Strike[”\"]"),
    "poison": ("Poison",
               r"\b[Aa]pply \d+ Poison|Poison to ALL",
               r"Poison is triggered|for each Poison|Poison on|equal to (the )?Poison"),
    "shiv": ("Shivs",
             r"Shivs? into your Hand|[Aa]dd \d+ Shivs?",
             r"Shivs? deal|[Ww]henever you play a Shiv|for each Shiv"),
    "discard": ("Discard / Sly",
                r"\b[Dd]iscard (\d+|a|your|any)",
                r"\bSly\b|[Ww]henever you discard|discarded this turn"),
    "orbs": ("Orbs",
             r"\bChannel\b",
             r"\bFocus\b|\bEvoke\b|for each Channeled|Orb slot"),
    "doom": ("Doom",
             r"\b[Aa]pply \d+ Doom|apply that much Doom",
             r"Doom on|for each Doom|as much Doom"),
    "osty": ("Osty / Summon",
             r"\bSummon \d+",
             r"\bOsty (deals|'s)|Osty's"),
    "stars": ("Stars",
              r"\b[Gg]ain \d+ Stars?\b",
              r"[Ww]henever you spend|for each Star|Stars? spent"),
    "forge": ("Forge",
              r"\bForge \d+",
              r"Sovereign Blade"),
}
_RX = {k: (re.compile(e) if e else None, re.compile(r) if r else None) for k, (_, e, r) in MECHANICS.items()}

# Mechanics that cost you something without a payoff (HP, cards, Stars): warn when the deck feeds them with nothing
# to reward it. Others (Vulnerable, Strength, Poison, ...) are useful on their own; payoffs only add to them.
NEEDS_PAYOFF = {"self_damage", "discard", "stars"}
# Mechanics where passed payoff cards are worth pointing out once the deck feeds them.
PAYOFF_MATTERS = NEEDS_PAYOFF | {"exhaust", "shiv"}


def label(key: str) -> str:
    return MECHANICS[key][0]


def tag_entry(name: str, text: str) -> tuple[list[str], list[str]]:
    """(mechanics this card/relic enables, mechanics it rewards)."""
    enables, rewards = [], []
    for k, (en, rw) in _RX.items():
        if en and en.search(text):
            enables.append(k)
        if rw and rw.search(text):
            rewards.append(k)
    if "Strike" in name.split():
        enables.append("strike")
    return enables, rewards
