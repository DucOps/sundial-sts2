"""Parse Slay the Spire 2 `.run` history files (schema v9/v10) into a compact run model.

Mirrors web/src/parse.js so the dashboard and the MCP server agree on every number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

ROOM = {"monster": "H", "elite": "E", "boss": "B", "unknown": "?", "rest_site": "R",
        "shop": "S", "treasure": "T", "ancient": "A"}
ROOM_NAME = {"H": "Hallway", "E": "Elite", "B": "Boss", "?": "Event", "R": "Rest",
             "S": "Shop", "T": "Treasure", "A": "Ancient"}
_SMALL = {"of", "the", "a", "an", "and", "in", "on", "to", "for", "with"}
_ENC_SUFFIX = re.compile(r"_(WEAK|NORMAL|ELITE|BOSS)$")


def strip_prefix(id_: str | None) -> str:
    if not id_ or not isinstance(id_, str):
        return ""
    return id_.split(".", 1)[1] if "." in id_ else id_


def title_case(raw: str) -> str:
    words = [w for w in raw.lower().split("_") if w]
    return " ".join(w if i and w in _SMALL else w.capitalize() for i, w in enumerate(words))


def pretty(id_: str | None) -> str:
    """'ENCOUNTER.PHROG_PARASITE_ELITE' -> 'Phrog Parasite'; 'STRIKE_IRONCLAD' -> 'Strike'."""
    s = strip_prefix(id_)
    if not s or s == "NONE":
        return ""
    s = _ENC_SUFFIX.sub("", s)
    s = re.sub(r"^(STRIKE|DEFEND)_(IRONCLAD|SILENT|DEFECT|NECROBINDER|REGENT|WATCHER)$", r"\1", s)
    return title_case(s)


def encounter_kind(id_: str) -> str:
    s = strip_prefix(id_)
    if s.endswith("_BOSS"):
        return "boss"
    if s.endswith("_ELITE"):
        return "elite"
    if s.endswith(("_WEAK", "_NORMAL")):
        return "monster"
    return ""


def is_encounter(model: str) -> bool:
    return bool(_ENC_SUFFIX.search(model))


def _choice_label(c: dict) -> str:
    key = ((c or {}).get("title") or {}).get("key") or ""
    m = re.search(r"options\.([A-Z0-9_]+)\.title$", key)
    if m:
        return title_case(m.group(1))
    return title_case(re.sub(r"\.title$", "", key)) if key else ""


@dataclass
class Floor:
    f: int                      # floor number across the whole run (1-based)
    act: int
    t: str                      # room glyph, see ROOM
    models: list[str]           # rooms visited on this map point (event, then encounter, ...)
    hp: int | None
    max_hp: int | None
    gold: int | None
    dmg: int = 0
    heal: int = 0
    max_hp_gain: int = 0
    max_hp_loss: int = 0
    turns: int = 0
    gold_gained: int = 0
    gold_spent: int = 0
    cards_picked: list[str] = field(default_factory=list)
    cards_skipped: list[str] = field(default_factory=list)
    relics_picked: list[str] = field(default_factory=list)
    relics_skipped: list[str] = field(default_factory=list)
    relics_bought: list[str] = field(default_factory=list)
    cards_bought: list[str] = field(default_factory=list)
    potions_picked: list[str] = field(default_factory=list)
    potions_used: list[str] = field(default_factory=list)
    potions_discarded: list[str] = field(default_factory=list)
    potions_bought: list[str] = field(default_factory=list)
    enchanted: list[tuple[str, str]] = field(default_factory=list)
    gold_lost: int = 0
    rest: str = ""
    upgraded: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    transformed: list[tuple[str, str]] = field(default_factory=list)
    gained_other: list[str] = field(default_factory=list)   # cards gained outside rewards (events, ancients)
    events: list[str] = field(default_factory=list)
    ancient_pick: str = ""
    ancient_options: list[str] = field(default_factory=list)

    @property
    def encounter(self) -> str:
        enc = [m for m in self.models if is_encounter(m)]
        return enc[-1] if enc else ""

    @property
    def hp_before(self) -> int | None:
        if self.hp is None:
            return None
        return self.hp + self.dmg - self.heal


@dataclass
class Run:
    id: int                     # start_time, also the file name
    key: str
    profile: str
    file: str
    character: str
    players: int
    ascension: int
    mode: str
    build: str
    seed: str
    start: int
    duration: int
    acts: list[str]
    outcome: str                # win | death | abandoned
    killer: str
    killer_kind: str
    floors: list[Floor]
    deck: list[dict]
    relics: list[dict]
    potions_held: list[str]
    badges: list[str]

    @property
    def floors_reached(self) -> int:
        return len(self.floors)

    @property
    def act_reached(self) -> int:
        return max((f.act for f in self.floors), default=0)

    @property
    def last(self) -> Floor | None:
        return self.floors[-1] if self.floors else None


def looks_like_run(d: Any) -> bool:
    return isinstance(d, dict) and isinstance(d.get("map_point_history"), list) \
        and isinstance(d.get("players"), list) and "start_time" in d


def parse_run(d: dict, profile: str = "", file: str = "") -> Run:
    player = (d.get("players") or [{}])[0]
    pid = player.get("id")
    floors: list[Floor] = []
    n = 0
    for ai, act in enumerate(d.get("map_point_history") or []):
        for pt in act or []:
            n += 1
            stats = pt.get("player_stats") or []
            ps = next((p for p in stats if p.get("player_id") == pid), stats[0] if stats else {})
            rooms = pt.get("rooms") or []
            cc = ps.get("card_choices") or []
            anc = next((x for x in ps.get("ancient_choice") or [] if x.get("was_chosen")), None)
            floors.append(Floor(
                f=n, act=ai + 1, t=ROOM.get(pt.get("map_point_type"), "?"),
                models=[strip_prefix(r.get("model_id")) for r in rooms if r.get("model_id")],
                hp=ps.get("current_hp"), max_hp=ps.get("max_hp"), gold=ps.get("current_gold"),
                dmg=ps.get("damage_taken") or 0, heal=ps.get("hp_healed") or 0,
                max_hp_gain=ps.get("max_hp_gained") or 0, max_hp_loss=ps.get("max_hp_lost") or 0,
                turns=sum(r.get("turns_taken") or 0 for r in rooms),
                gold_gained=ps.get("gold_gained") or 0, gold_spent=ps.get("gold_spent") or 0,
                cards_picked=[strip_prefix(c["card"]["id"]) for c in cc if c.get("was_picked")],
                cards_skipped=[strip_prefix(c["card"]["id"]) for c in cc if not c.get("was_picked")],
                relics_picked=[strip_prefix(r.get("choice")) for r in ps.get("relic_choices") or [] if r.get("was_picked")],
                relics_skipped=[strip_prefix(r.get("choice")) for r in ps.get("relic_choices") or [] if not r.get("was_picked")],
                relics_bought=[strip_prefix(x) for x in ps.get("bought_relics") or []],
                cards_bought=[strip_prefix(x) for x in ps.get("bought_colorless") or []],
                potions_picked=[strip_prefix(r.get("choice")) for r in ps.get("potion_choices") or [] if r.get("was_picked")],
                potions_used=[strip_prefix(x) for x in ps.get("potion_used") or []],
                potions_discarded=[strip_prefix(x) for x in ps.get("potion_discarded") or []],
                potions_bought=[strip_prefix(x) for x in ps.get("bought_potions") or []],
                enchanted=[(strip_prefix((c.get("card") or {}).get("id")), strip_prefix(c.get("enchantment")))
                           for c in ps.get("cards_enchanted") or []],
                gold_lost=(ps.get("gold_lost") or 0) + (ps.get("gold_stolen") or 0),
                rest=((ps.get("rest_site_choices") or [""])[0] or ""),
                upgraded=[strip_prefix(x) for x in ps.get("upgraded_cards") or []],
                removed=[strip_prefix((c or {}).get("id")) for c in ps.get("cards_removed") or []],
                transformed=[(strip_prefix(c["original_card"]["id"]), strip_prefix(c["final_card"]["id"]))
                             for c in ps.get("cards_transformed") or []],
                gained_other=[strip_prefix((c or {}).get("id")) for c in ps.get("cards_gained") or []
                              if strip_prefix((c or {}).get("id")) not in
                              [strip_prefix(x["card"]["id"]) for x in cc if x.get("was_picked")]],
                events=[x for x in (_choice_label(c) for c in ps.get("event_choices") or []) if x],
                ancient_pick=(anc or {}).get("TextKey", ""),
                ancient_options=[x.get("TextKey", "") for x in ps.get("ancient_choice") or []],
            ))
    enc = d.get("killed_by_encounter") or ""
    ev = d.get("killed_by_event") or ""
    enc = "" if enc == "NONE.NONE" else enc
    ev = "" if ev == "NONE.NONE" else ev
    outcome = "win" if d.get("win") else ("abandoned" if d.get("was_abandoned") else "death")
    start = int(d.get("start_time") or 0)
    return Run(
        id=start, key=f"{d.get('seed', '')}-{start}", profile=profile, file=file,
        character=strip_prefix(player.get("character")), players=len(d.get("players") or []),
        ascension=int(d.get("ascension") or 0), mode=d.get("game_mode") or "standard",
        build=d.get("build_id") or "", seed=d.get("seed") or "", start=start,
        duration=int(d.get("run_time") or 0), acts=[strip_prefix(a) for a in d.get("acts") or []],
        outcome=outcome,
        killer=strip_prefix(enc) if enc else strip_prefix(ev),
        killer_kind=(encounter_kind(enc) or "monster") if enc else ("event" if ev else ""),
        floors=floors,
        deck=[{"id": strip_prefix(c.get("id")), "up": c.get("current_upgrade_level") or 0,
               "ench": strip_prefix((c.get("enchantment") or {}).get("id")), "floor": c.get("floor_added_to_deck")}
              for c in player.get("deck") or []],
        relics=[{"id": strip_prefix(r.get("id")), "floor": r.get("floor_added_to_deck") or 0}
                for r in player.get("relics") or []],
        potions_held=[strip_prefix(p.get("id")) for p in player.get("potions") or []],
        badges=[strip_prefix(b.get("id")) for b in player.get("badges") or []],
    )
