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


def _dicts(value: Any) -> list[dict]:
    """The dict entries of a save-file list. A half-written or older-schema file can put anything in there, and one
    odd entry must not cost the whole run."""
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [x for x in value if isinstance(x, str)] if isinstance(value, list) else []


def _id_of(entry: Any, *path: str) -> str:
    """The id nested inside a save-file entry ('card' -> 'id'), '' when the entry or any step is missing."""
    cur = entry
    for key in path:
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(key)
    return strip_prefix(cur) if isinstance(cur, str) else ""


def _num(value: Any) -> int | None:
    """A whole-number save-file field as an int: None when it is missing or not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(round(value))


def _enchantment_of(entry: dict) -> str:
    """The enchantment id of a card entry: the save writes it as a bare id in some places and as {'id': ...}
    in others, so accept both."""
    value = entry.get("enchantment")
    return strip_prefix(value) if isinstance(value, str) else _id_of(entry, "enchantment", "id")


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
        for pt in _dicts(act):
            n += 1
            stats = _dicts(pt.get("player_stats"))
            ps = next((p for p in stats if p.get("player_id") == pid), stats[0] if stats else {})
            rooms = _dicts(pt.get("rooms"))
            cc = _dicts(ps.get("card_choices"))
            picked = [i for i in (_id_of(c, "card", "id") for c in cc if c.get("was_picked")) if i]
            skipped = [i for i in (_id_of(c, "card", "id") for c in cc if not c.get("was_picked")) if i]
            ancient = _dicts(ps.get("ancient_choice"))
            anc = next((x for x in ancient if x.get("was_chosen")), None)
            transformed = []
            for c in _dicts(ps.get("cards_transformed")):
                before, after = _id_of(c, "original_card", "id"), _id_of(c, "final_card", "id")
                if before and after:
                    transformed.append((before, after))
            enchanted = []
            for c in _dicts(ps.get("cards_enchanted")):
                card_id = _id_of(c, "card", "id")
                if card_id:
                    enchanted.append((card_id, _enchantment_of(c)))
            rest_choices = _strings(ps.get("rest_site_choices"))
            floors.append(Floor(
                f=n, act=ai + 1, t=ROOM.get(pt.get("map_point_type"), "?"),
                models=[strip_prefix(r.get("model_id")) for r in rooms if r.get("model_id")],
                hp=_num(ps.get("current_hp")), max_hp=_num(ps.get("max_hp")), gold=_num(ps.get("current_gold")),
                dmg=_num(ps.get("damage_taken")) or 0, heal=_num(ps.get("hp_healed")) or 0,
                max_hp_gain=_num(ps.get("max_hp_gained")) or 0, max_hp_loss=_num(ps.get("max_hp_lost")) or 0,
                turns=sum(_num(r.get("turns_taken")) or 0 for r in rooms),
                gold_gained=_num(ps.get("gold_gained")) or 0, gold_spent=_num(ps.get("gold_spent")) or 0,
                cards_picked=picked, cards_skipped=skipped,
                relics_picked=[i for i in (_id_of(r, "choice") for r in _dicts(ps.get("relic_choices")) if r.get("was_picked")) if i],
                relics_skipped=[i for i in (_id_of(r, "choice") for r in _dicts(ps.get("relic_choices")) if not r.get("was_picked")) if i],
                relics_bought=[i for i in map(strip_prefix, _strings(ps.get("bought_relics"))) if i],
                cards_bought=[i for i in map(strip_prefix, _strings(ps.get("bought_colorless"))) if i],
                potions_picked=[i for i in (_id_of(r, "choice") for r in _dicts(ps.get("potion_choices")) if r.get("was_picked")) if i],
                potions_used=[i for i in map(strip_prefix, _strings(ps.get("potion_used"))) if i],
                potions_discarded=[i for i in map(strip_prefix, _strings(ps.get("potion_discarded"))) if i],
                potions_bought=[i for i in map(strip_prefix, _strings(ps.get("bought_potions"))) if i],
                enchanted=enchanted,
                gold_lost=(_num(ps.get("gold_lost")) or 0) + (_num(ps.get("gold_stolen")) or 0),
                rest=rest_choices[0] if _strings(rest_choices) else "",
                upgraded=[i for i in map(strip_prefix, _strings(ps.get("upgraded_cards"))) if i],
                removed=[i for i in (_id_of(c, "id") for c in _dicts(ps.get("cards_removed"))) if i],
                transformed=transformed,
                gained_other=[i for i in (_id_of(c, "id") for c in _dicts(ps.get("cards_gained"))) if i and i not in picked],
                events=[x for x in (_choice_label(c) for c in _dicts(ps.get("event_choices"))) if x],
                ancient_pick=(anc or {}).get("TextKey", ""),
                ancient_options=[x.get("TextKey", "") for x in ancient],
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
        ascension=int(_num(d.get("ascension")) or 0), mode=d.get("game_mode") or "standard",
        build=d.get("build_id") or "", seed=d.get("seed") or "", start=start,
        duration=int(_num(d.get("run_time")) or 0), acts=[strip_prefix(a) for a in _strings(d.get("acts"))],
        outcome=outcome,
        killer=strip_prefix(enc) if enc else strip_prefix(ev),
        killer_kind=(encounter_kind(enc) or "monster") if enc else ("event" if ev else ""),
        floors=floors,
        deck=[{"id": strip_prefix(c.get("id")), "up": _num(c.get("current_upgrade_level")) or 0,
               "ench": _enchantment_of(c), "floor": _num(c.get("floor_added_to_deck"))}
              for c in _dicts(player.get("deck"))],
        relics=[{"id": strip_prefix(r.get("id")), "floor": _num(r.get("floor_added_to_deck")) or 0}
                for r in _dicts(player.get("relics"))],
        potions_held=[i for i in map(strip_prefix, (p.get("id") for p in _dicts(player.get("potions")))) if i],
        badges=[i for i in map(strip_prefix, (b.get("id") for b in _dicts(player.get("badges")))) if i],
    )
