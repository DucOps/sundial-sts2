"""Parse Slay the Spire 2 `.run` history files (schema v8–v11) into a compact run model.

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
# The game's GameMode enum (sts2.dll, MegaCrit.Sts2.Core.Runs): saves store it lower-cased in `game_mode`.
# Blitz (v0.113+) has its own A1–A5 ladder shared by all characters and a fixed 8-floor act (Ancient, two fights,
# merchant, elite, treasure, rest, boss); Dread (v0.113+) turns every ascension modifier on. So runs are only
# compared, and ascensions only climbed, within one mode. Custom games (`is_custom_game`, v11+) are never compared.
MODES = ("standard", "daily", "blitz", "dread")
MODE_NAME = {"standard": "Standard", "daily": "Daily", "blitz": "Blitz", "dread": "Dread", "custom": "Custom"}
_SMALL = {"of", "the", "a", "an", "and", "in", "on", "to", "for", "with"}
_ENC_SUFFIX = re.compile(r"_(WEAK|NORMAL|ELITE|BOSS)$")
FIGHT_ROOMS = ("monster", "elite", "boss")


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
    s = re.sub(r"^(STRIKE|DEFEND)_(IRONCLAD|SILENT|DEFECT|NECROBINDER|REGENT|FOOL|WATCHER)$", r"\1", s)
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


# Readers for save-file fields. A save from another game version (or a half-written file) can hold a list
# where an object was expected, an id as an object or a string, or null; one odd entry must never cost the run.
def _list(v: Any) -> list:
    return v if isinstance(v, list) else []


def _objs(v: Any) -> list[dict]:
    """The dict entries of a list field (anything else is skipped)."""
    return [x for x in _list(v) if isinstance(x, dict)]


def _ref(v: Any) -> str:
    """An id stored as 'CARD.X', as {"id": "CARD.X"}, or missing -> 'X' or ''."""
    if isinstance(v, dict):
        v = v.get("id")
    return strip_prefix(v) if isinstance(v, str) else ""


def _refs(v: Any) -> list[str]:
    return [x for x in map(_ref, _list(v)) if x]


def _sub(d: dict, key: str) -> str:
    """The id of a nested object, e.g. _sub(choice, "card") for {"card": {"id": ...}}."""
    return _ref(d.get(key))


def _int(v: Any) -> int:
    """A whole number from a number or numeric string; 0 otherwise."""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(float(v))
        except ValueError:
            return 0
    return 0


def _opt_int(v: Any) -> int | None:
    return None if v is None or isinstance(v, bool) or not isinstance(v, (int, float)) else int(v)


def _first_str(v: Any) -> str:
    """rest_site_choices: normally ['SMITH'], read a bare 'SMITH' too."""
    if isinstance(v, str):
        return v
    return next((x for x in _list(v) if isinstance(x, str)), "")


def is_encounter(model: str) -> bool:
    return bool(_ENC_SUFFIX.search(model))


def _choice_label(c: dict) -> str:
    title = c.get("title") if isinstance(c, dict) else None
    key = title.get("key") if isinstance(title, dict) else ""
    key = key if isinstance(key, str) else ""
    m = re.search(r"options\.([A-Z0-9_]+)\.title$", key)
    if m:
        return title_case(m.group(1))
    return title_case(re.sub(r"\.title$", "", key).rsplit(".", 1)[-1]) if key else ""      # 'BLITZ.NEOW.title' -> 'Neow'


def _service(c: dict) -> str:
    """A Blitz merchant service: 'card_removal', or 'prismatic_card_reward:SILENT' when it names a model."""
    t = c.get("type") if isinstance(c.get("type"), str) else ""
    m = _ref(c.get("model_id"))
    return f"{t}:{m}" if t and m else t


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
    room: str = ""              # the last room's type: a ? map point can turn out to be a shop, a treasure or a fight
    fight: str = ""             # the encounter fought here (some ids have no _WEAK/_NORMAL suffix, e.g. OVERGROWTH_CRAWLERS)
    merchant: bool = False      # a Blitz merchant: card choices here are rewards from a service, not shop stock
    services_picked: list[str] = field(default_factory=list)    # Blitz merchant services, see _service
    services_skipped: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    ancient_pick: str = ""
    ancient_options: list[str] = field(default_factory=list)

    @property
    def encounter(self) -> str:
        if self.fight:
            return self.fight
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
    custom: bool = False        # a custom game (v11+): never compared with or climbed alongside normal runs

    @property
    def mode_name(self) -> str:
        return MODE_NAME.get(self.mode, title_case(self.mode))

    @property
    def bucket(self) -> str:
        """What the run is compared within: its game mode, or 'custom' for a custom game whatever its mode."""
        return "custom" if self.custom else self.mode

    @property
    def level(self) -> str:
        """'A7' for a Standard run, 'Blitz A3' / 'Daily A0' / 'Dread A10' / 'Custom A7' otherwise."""
        b = self.bucket
        return f"A{self.ascension}" if b == "standard" else f"{MODE_NAME.get(b, title_case(b))} A{self.ascension}"

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
    players = _objs(d.get("players"))
    player = players[0] if players else {}
    pid = player.get("id")
    floors: list[Floor] = []
    n = 0
    mode = d.get("game_mode")
    mode = mode.lower() if isinstance(mode, str) and mode else "standard"
    for ai, act in enumerate(_list(d.get("map_point_history"))):
        for pt in _objs(act):
            n += 1
            stats = _objs(pt.get("player_stats"))
            ps = next((p for p in stats if p.get("player_id") == pid), stats[0] if stats else {})
            rooms = _objs(pt.get("rooms"))
            cc = _objs(ps.get("card_choices"))
            picked = [x for x in (_sub(c, "card") for c in cc if c.get("was_picked")) if x]
            skipped = [x for x in (_sub(c, "card") for c in cc if not c.get("was_picked")) if x]
            gained = _refs(ps.get("cards_gained"))
            t = ROOM.get(pt.get("map_point_type"), "?")
            fights = [_ref(r.get("model_id")) for r in rooms if r.get("room_type") in FIGHT_ROOMS and _ref(r.get("model_id"))]
            room = next((r["room_type"] for r in reversed(rooms) if isinstance(r.get("room_type"), str)), "")
            anc_opts = _objs(ps.get("ancient_choice"))
            anc = next((x for x in anc_opts if x.get("was_chosen")), {})
            if t in ("A", "?") and room != "shop" and not fights and not anc and skipped and not picked:
                # Choose-N screens at events (Room Full of Cheese, Brain Leech, Blitz Neow) list only the cards
                # left behind; the ones taken are in cards_gained
                picked = [x for x in gained if x not in skipped]
            services = _objs(ps.get("blitz_merchant_choices"))
            relic_ch, potion_ch = _objs(ps.get("relic_choices")), _objs(ps.get("potion_choices"))
            floors.append(Floor(
                f=n, act=ai + 1, t=t,
                models=[x for x in (_ref(r.get("model_id")) for r in rooms) if x],
                hp=_opt_int(ps.get("current_hp")), max_hp=_opt_int(ps.get("max_hp")),
                gold=_opt_int(ps.get("current_gold")),
                dmg=_int(ps.get("damage_taken")), heal=_int(ps.get("hp_healed")),
                max_hp_gain=_int(ps.get("max_hp_gained")), max_hp_loss=_int(ps.get("max_hp_lost")),
                turns=sum(_int(r.get("turns_taken")) for r in rooms),
                gold_gained=_int(ps.get("gold_gained")), gold_spent=_int(ps.get("gold_spent")),
                cards_picked=picked,
                cards_skipped=skipped,
                relics_picked=[x for x in (_ref(r.get("choice")) for r in relic_ch if r.get("was_picked")) if x],
                relics_skipped=[x for x in (_ref(r.get("choice")) for r in relic_ch if not r.get("was_picked")) if x],
                relics_bought=_refs(ps.get("bought_relics")),
                cards_bought=_refs(ps.get("bought_colorless")),
                potions_picked=[x for x in (_ref(r.get("choice")) for r in potion_ch if r.get("was_picked")) if x],
                potions_used=_refs(ps.get("potion_used")),
                potions_discarded=_refs(ps.get("potion_discarded")),
                potions_bought=_refs(ps.get("bought_potions")),
                enchanted=[(_sub(c, "card"), _sub(c, "enchantment")) for c in _objs(ps.get("cards_enchanted"))],
                gold_lost=_int(ps.get("gold_lost")) + _int(ps.get("gold_stolen")),
                rest=_first_str(ps.get("rest_site_choices")),
                upgraded=_refs(ps.get("upgraded_cards")),
                removed=_refs(ps.get("cards_removed")),
                transformed=[(_sub(c, "original_card"), _sub(c, "final_card"))
                             for c in _objs(ps.get("cards_transformed"))],
                gained_other=[x for x in gained if x not in picked],
                room=room, fight=fights[-1] if fights else "",
                merchant=t == "S" and (mode == "blitz" or isinstance(ps.get("blitz_merchant_choices"), list)),
                services_picked=[x for x in (_service(c) for c in services if c.get("was_picked")) if x],
                services_skipped=[x for x in (_service(c) for c in services if not c.get("was_picked")) if x],
                events=[x for x in (_choice_label(c) for c in _objs(ps.get("event_choices"))) if x],
                ancient_pick=anc.get("TextKey") if isinstance(anc.get("TextKey"), str) else "",
                ancient_options=[x["TextKey"] for x in anc_opts if isinstance(x.get("TextKey"), str)],
            ))
    enc = d.get("killed_by_encounter") if isinstance(d.get("killed_by_encounter"), str) else ""
    ev = d.get("killed_by_event") if isinstance(d.get("killed_by_event"), str) else ""
    enc = "" if enc == "NONE.NONE" else enc
    ev = "" if ev == "NONE.NONE" else ev
    outcome = "win" if d.get("win") else ("abandoned" if d.get("was_abandoned") else "death")
    start = _int(d.get("start_time"))
    return Run(
        id=start, key=f"{d.get('seed', '')}-{start}", profile=profile, file=file,
        character=_ref(player.get("character")), players=len(players),
        ascension=_int(d.get("ascension")), mode=mode,
        build=str(d.get("build_id") or ""), seed=str(d.get("seed") or ""), start=start,
        duration=_int(d.get("run_time")), acts=_refs(d.get("acts")),
        outcome=outcome,
        killer=strip_prefix(enc) if enc else strip_prefix(ev),
        killer_kind=(encounter_kind(enc) or "monster") if enc else ("event" if ev else ""),
        floors=floors,
        deck=[{"id": _ref(c), "up": _int(c.get("current_upgrade_level")), "ench": _sub(c, "enchantment"),
               "floor": _opt_int(c.get("floor_added_to_deck"))}
              for c in _objs(player.get("deck")) if _ref(c)],
        relics=[{"id": _ref(r), "floor": _int(r.get("floor_added_to_deck"))}
                for r in _objs(player.get("relics")) if _ref(r)],
        potions_held=_refs(player.get("potions")),
        badges=_refs(player.get("badges")),
        custom=d.get("is_custom_game") is True,
    )
