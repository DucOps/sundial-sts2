"""The rest of the game's facts, from the same install gamedata.py reads: characters (starting HP, gold, deck, relic),
monsters (HP, moves, intents and their numbers per ascension), encounters (room type, monsters, act), acts, orbs,
ascension levels and the game's glossary of terms.

Numbers that change with ascension are stored as {"base": n, "asc": m, "from": level}: the game's own
GetValueIfAscension(level, value at that ascension, default). Level 8 is Tough Enemies (HP), 9 Deadly Enemies
(damage). Anything this reader can't evaluate is left out rather than guessed.
"""
from __future__ import annotations

import re
from decimal import Decimal

from .gamedata import NS, Dll, clean, norm

ROOM = {1: "hallway", 2: "elite", 3: "boss"}
INTENT = {"SingleAttackIntent": "attack", "MultiAttackIntent": "multi-attack", "DefendIntent": "defend",
          "BuffIntent": "buff", "DebuffIntent": "debuff", "StatusIntent": "adds status cards",
          "CardDebuffIntent": "debuffs cards", "SummonIntent": "summon", "HealIntent": "heal", "StunIntent": "stunned",
          "SleepIntent": "asleep", "HiddenIntent": "hidden", "EscapeIntent": "escape", "DeathBlowIntent": "death blow"}


# ---------------------------------------------------------------- values
def value(v) -> int | float | dict | None:
    """A Decimal or an ascension pair as JSON; None when the reader couldn't evaluate it."""
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, tuple) and v[:1] == ("asc",) and all(isinstance(x, Decimal) for x in v[1:]):
        lvl, asc, base = (value(x) for x in v[1:])
        return base if asc == base else {"base": base, "asc": asc, "from": lvl}
    return None


def at(v, ascension: int | None):
    """A stored value at a given ascension (None: the default)."""
    if isinstance(v, dict):
        return v["asc"] if ascension is not None and ascension >= v["from"] else v["base"]
    return v


def show(v, ascension: int | None = None) -> str:
    """'22 (26 from A9)', or just the value at `ascension` when one is given."""
    if ascension is not None or not isinstance(v, dict):
        return str(at(v, ascension))
    return f"{v['base']} ({v['asc']} from A{v['from']})"


def words(name: str) -> str:
    """'EyeLasersDamage' -> 'Eye Lasers Damage'."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)


def getter(dll: Dll, meths: dict, name: str, depth: int = 0):
    """Evaluate a property getter of the same type, following simple getter-to-getter chains."""
    m = meths.get(name)
    if m is None or not m.Rva or depth > 3:
        return None
    try:
        ret, _ = dll.run(m.Rva)
    except Exception:          # noqa: BLE001  an unusual body; leave the value out
        return None
    if isinstance(ret, tuple) and ret[:1] == ("ret",):
        # follow only a plain 'return OtherGetter' (3 ops); anything with arithmetic is left out, not guessed
        if ret[1] in meths and len(dll.ops(m.Rva)) == 3:
            return getter(dll, meths, ret[1], depth + 1)
        return None
    return ret


def _generic_models(dll: Dll, rva: int, wanted: set[str]) -> list[str]:
    """Generic type arguments in a body that name one of `wanted` (ModelDb.Monster<Axebot>() etc.), in order."""
    out = []
    for _o, _m, gargs in dll.calls(rva):
        out += [g for g in gargs if g in wanted]
    return out


def _models(v) -> list[str]:
    if isinstance(v, list):
        return [x for item in v[1:] for x in _models(item)]
    if isinstance(v, tuple) and v[:1] == ("model",):
        return [v[1]]
    if isinstance(v, tuple) and v[:1] == ("obj",):
        return [x for a in v[2] for x in _models(a)]
    return []


def _types(dll: Dll, ns: str) -> dict[str, int]:
    return {n: t for (tns, n), t in dll.types.items()
            if tns == f"{NS}.{ns}" and not n.startswith(("Mock", "Deprecated")) and "<" not in n}


def _keys(table: dict, suffix: str) -> dict[str, str]:
    """norm(class name) -> localisation key, for keys like 'AEONGLASS.name'."""
    return {norm(k[:-len(suffix)]): k[:-len(suffix)] for k in table if k.endswith(suffix) and k.count(".") == 1}


# ---------------------------------------------------------------- entries
def build_world(dll: Dll, loc: dict, version: str, src: str, names: dict[str, dict[str, str]]) -> list[dict]:
    """`names`: {kind: {class name: display name}} for cards and relics already built (to name starter decks)."""
    out: list[dict] = []
    base = {"source": src, "as_of": version}
    card_cls, relic_cls = names.get("card", {}), names.get("relic", {})

    # --- characters
    chars = loc.get("characters.json", {})
    keys = _keys(chars, ".title")
    for cls, t in _types(dll, "Characters").items():
        key = keys.get(norm(cls))
        m = dll.methods_of(t)
        if not key or "get_StartingHp" not in m or cls not in names.get("pool_owners", {cls: cls}):
            continue                                # skips placeholder characters (Random, Deprived)
        hp, gold = value(getter(dll, m, "get_StartingHp")), value(getter(dll, m, "get_StartingGold"))
        deck = _models(getter(dll, m, "get_StartingDeck")) or _generic_models(dll, m["get_StartingDeck"].Rva, set(card_cls))
        relics = _models(getter(dll, m, "get_StartingRelics")) or _generic_models(
            dll, m["get_StartingRelics"].Rva, set(relic_cls))
        counts: dict[str, int] = {}
        for c in deck:
            counts[card_cls.get(c, words(c))] = counts.get(card_cls.get(c, words(c)), 0) + 1
        kit = [f"Starts with {hp} HP" if hp is not None else "", f"{gold} gold" if gold is not None else "",
               "relic " + ", ".join(relic_cls.get(r, words(r)) for r in relics) if relics else "",
               "deck: " + ", ".join(f"{n} {c}" for c, n in counts.items()) if counts else ""]
        text = clean(chars.get(f"{key}.description", "")) + " " + ", ".join(k for k in kit if k) + "."
        out.append({**base, "id": key, "kind": "character", "name": clean(chars.get(f"{key}.title", cls)),
                    "text": text.strip(), "hp": hp, "gold": gold,
                    "starting_deck": [card_cls.get(c, words(c)) for c in deck],
                    "starting_relics": [relic_cls.get(r, words(r)) for r in relics]})

    # --- monsters
    mons = loc.get("monsters.json", {})
    mkeys = _keys(mons, ".name")
    mon_types = _types(dll, "Monsters")
    card_types = set(_types(dll, "Cards"))
    monster_name: dict[str, str] = {}
    monster_id: dict[str, str] = {}
    for cls, t in mon_types.items():
        key = mkeys.get(norm(cls))
        if not key:
            continue
        m = dll.methods_of(t)
        hp_min, hp_max = value(getter(dll, m, "get_MinInitialHp")), value(getter(dll, m, "get_MaxInitialHp"))
        # the async body of each move lives in a nested state-machine type '<EbbMove>d__34'
        bodies = {}
        for nt in dll.nested(t):
            nm = dll._names[nt]
            mm = re.match(r"<(\w+)>d__\d+", nm)
            mn = dll.methods_of(nt).get("MoveNext")
            if mm and mn is not None and mn.Rva:
                bodies[mm.group(1)] = mn.Rva
        moves = []
        gm = m.get("GenerateMoveStateMachine")
        if gm is not None and gm.Rva:
            cur = None
            pending: list[str] = []
            for op, a in dll.ops(gm.Rva):
                if op == "ldstr":
                    sid = dll.string(a)
                    if sid.endswith("_MOVE"):
                        mid = sid.removesuffix("_MOVE")
                        cur = {"id": mid, "name": clean(mons.get(f"{key}.moves.{mid}.title", words(mid.title()))),
                               "intents": [], "values": {}}
                        moves.append(cur)
                elif op in ("call", "callvirt", "newobj") and cur is not None:
                    owner, mname, *_rest = dll.method(a)
                    if owner == cls and mname.startswith("get_"):
                        pending.append(mname)
                    elif op == "newobj" and owner in INTENT:
                        cur["intents"].append(INTENT[owner])
                        for g in pending:
                            cur["values"].setdefault(g[4:], value(getter(dll, m, g)))
                        pending = []
                    elif op == "newobj" and owner == "MoveState":
                        pending = []
            for mv in moves:
                body = bodies.get("".join(w.capitalize() for w in mv["id"].split("_")) + "Move")
                if not body:
                    continue
                powers, cards = [], []
                for owner, mname, gargs in dll.calls(body):
                    if owner == cls and mname.startswith("get_"):
                        mv["values"].setdefault(mname[4:], value(getter(dll, m, mname)))
                    for g in gargs:
                        if g.endswith("Power") and owner == "PowerCmd":
                            powers.append(words(g.removesuffix("Power")))
                        elif g in card_types:
                            cards.append(card_cls.get(g, words(g)))
                if powers:
                    mv["powers"] = sorted(set(powers))
                if cards:
                    mv["cards"] = sorted(set(cards))
        for mv in moves:
            mv["values"] = {k: v for k, v in mv["values"].items() if v is not None}
        name = clean(mons.get(f"{key}.name", words(cls)))
        monster_name[cls], monster_id[cls] = name, key
        hp_text = ("HP " + show(hp_min) + (f" to {show(hp_max)}" if hp_max not in (None, hp_min) else "")) \
            if hp_min is not None else "HP unknown"
        lines = []
        for mv in moves:
            bits = [", ".join(dict.fromkeys(mv["intents"])) or "no intent"]
            bits += [f"{words(k)} {show(v)}" for k, v in mv["values"].items()]
            if mv.get("powers"):
                bits.append("powers: " + ", ".join(mv["powers"]))
            if mv.get("cards"):
                bits.append("cards: " + ", ".join(mv["cards"]))
            lines.append(f"{mv['name']} ({'; '.join(bits)})")
        out.append({**base, "id": key, "kind": "monster", "name": name, "hp": hp_min, "hp_max": hp_max,
                    "moves": moves, "text": f"{hp_text}. Moves: " + (" · ".join(lines) or "unknown") + "."})

    # --- acts (which encounters, bosses, ancients and events each act has)
    enc_types = _types(dll, "Encounters")
    act_of: dict[str, list[str]] = {}
    events = loc.get("events.json", {})
    ekeys = _keys(events, ".title")
    acts_loc = loc.get("acts.json", {})
    for cls, t in _types(dll, "Acts").items():
        m = dll.methods_of(t)
        get = lambda n, wanted: _generic_models(dll, m[n].Rva, wanted) if m.get(n) is not None and m[n].Rva else []
        encs = list(dict.fromkeys(get("GenerateAllEncounters", set(enc_types))))
        bosses = list(dict.fromkeys(get("get_BossDiscoveryOrder", set(enc_types))))
        ev_types = set(_types(dll, "Events"))
        ancients = list(dict.fromkeys(get("get_AllAncients", ev_types)))
        evs = list(dict.fromkeys(get("get_AllEvents", ev_types)))
        name = next((clean(v) for k, v in acts_loc.items() if norm(k.split(".")[0]) == norm(cls) and k.endswith("title")),
                     words(cls))
        for e in encs + bosses:
            act_of.setdefault(e, []).append(name)
        ev_name = lambda c: clean(events.get(f"{ekeys.get(norm(c), '')}.title", words(c)))
        out.append({**base, "id": cls.upper(), "kind": "act", "name": name,
                    "text": f"Bosses: {', '.join(words(b).removesuffix(' Boss') for b in bosses) or '—'}. "
                            f"Ancients: {', '.join(ev_name(a) for a in ancients) or '—'}. "
                            f"Events: {', '.join(ev_name(e) for e in evs) or '—'}. "
                            f"{len(encs)} encounters (see kind 'encounter').",
                    "bosses": bosses, "ancients": ancients, "events": evs, "encounters": encs})

    # --- encounters
    encl = loc.get("encounters.json", {})
    ekeys = _keys(encl, ".title")
    for cls, t in enc_types.items():
        key = ekeys.get(norm(cls))
        if not key:
            continue
        m = dll.methods_of(t)
        rt = getter(dll, m, "get_RoomType")
        room = ROOM.get(int(rt)) if isinstance(rt, Decimal) else None
        found: list[str] = []
        for n in ("GenerateMonsters", "get_AllPossibleMonsters"):
            if m.get(n) is not None and m[n].Rva:
                found += _generic_models(dll, m[n].Rva, set(mon_types))
        found = list(dict.fromkeys(found))
        kind = room or ("event fight" if "Event" in cls else "fight")
        if cls.endswith("Weak") and room == "hallway":
            kind = "hallway (early, weak)"
        acts = list(dict.fromkeys(act_of.get(cls, [])))
        out.append({**base, "id": key, "kind": "encounter", "name": clean(encl.get(f"{key}.title", words(cls))),
                    "room": room, "acts": acts, "monsters": [monster_id.get(x, x.upper()) for x in found],
                    "text": f"{kind.capitalize()}" + (f" in {', '.join(acts)}" if acts else "")
                            + (f". Monsters: {', '.join(monster_name.get(x, words(x)) for x in found)}."
                               if found else ". Monsters: not readable from the game files.")})

    # --- orbs
    orbs = loc.get("orbs.json", {})
    for cls, t in _types(dll, "Orbs").items():
        key = next((k[:-6] for k in orbs if k.endswith(".title") and norm(k[:-6]) in (norm(cls), norm(cls) + "ORB")), None)
        if not key:
            continue
        m = dll.methods_of(t)
        vals = {"Passive": value(getter(dll, m, "get_PassiveVal")), "Evoke": value(getter(dll, m, "get_EvokeVal"))}
        smart = orbs.get(f"{key}.smartDescription", "")
        text = clean(re.sub(r"\{(\w+)\}", lambda x: show(vals[x.group(1)]) if vals.get(x.group(1)) is not None
                            else "X", smart)) if smart else clean(orbs.get(f"{key}.description", ""))
        out.append({**base, "id": key, "kind": "orb", "name": clean(orbs.get(f"{key}.title", words(cls))), "text": text})

    # --- ascension levels and the glossary of terms
    asc = loc.get("ascension.json", {})
    for k in sorted(asc):
        mm = re.match(r"LEVEL_(\d+)\.title$", k)
        if mm and int(mm.group(1)) > 0:
            lvl = int(mm.group(1))
            out.append({**base, "id": f"A{lvl}", "kind": "ascension", "name": f"A{lvl} {clean(asc[k])}",
                        "text": clean(asc.get(f"LEVEL_{mm.group(1)}.description", ""))})
    tips = loc.get("static_hover_tips.json", {})
    for k in sorted(tips):
        if k.endswith(".title") and k.count(".") == 1:
            key = k[:-6]
            text = clean(tips.get(f"{key}.description", ""))
            if text and "{" not in text and "{" not in tips[k]:
                out.append({**base, "id": key, "kind": "term", "name": clean(tips[k]), "text": text})
    return out


# ---------------------------------------------------------------- rendering for the run summary
def monster_line(e: dict, ascension: int | None) -> str:
    """One monster at a given ascension: 'Aeonglass 535 HP: Ebb (attack 26, ...) · ...'."""
    hp = e.get("hp")
    bits = []
    for mv in e.get("moves") or []:
        parts = [", ".join(dict.fromkeys(mv.get("intents") or [])) or "no intent"]
        parts += [f"{words(k)} {at(v, ascension)}" for k, v in (mv.get("values") or {}).items()]
        if mv.get("powers"):
            parts.append("powers: " + ", ".join(mv["powers"]))
        if mv.get("cards"):
            parts.append("cards: " + ", ".join(mv["cards"]))
        bits.append(f"{mv['name']} ({'; '.join(parts)})")
    return (f"{e['name']} {at(hp, ascension)} HP" if hp is not None else f"{e['name']} (HP not readable)") \
        + (": " + " · ".join(bits) if bits else "")
