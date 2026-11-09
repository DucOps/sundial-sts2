"""Turn a run into a compact, fact-checked summary for an AI analyst, and compute
the player's own baselines so every number can be compared with "what's normal for me".
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean, median

from .annotations import ROLE_LABEL, ROLES, Annotations, is_basic
from .knowledge import Knowledge
from .mechanics import MECHANICS, NEEDS_PAYOFF, PAYOFF_MATTERS
from .mechanics import label as mech_label
from .gameworld import monster_line
from .parse import ROOM_NAME, Floor, Run, encounter_kind, pretty, strip_prefix

_basic = is_basic


def fmt_date(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%a %d %b %Y %H:%M")


def fmt_dur(sec: int) -> str:
    h, m = divmod(round(sec / 60), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def outcome_line(r: Run) -> str:
    if r.outcome == "win":
        return f"Victory on floor {r.floors_reached}"
    last = r.last
    where = f"Act {last.act} {ROOM_NAME[last.t].lower()}" if last else ""
    if r.outcome == "abandoned":
        return f"Abandoned on floor {r.floors_reached} ({where})"
    return f"Died on floor {r.floors_reached} ({where}) to {pretty(r.killer) or 'unknown'}"


# ---------------------------------------------------------------- run lookup
def resolve(runs: list[Run], ref: str | int | None) -> Run | None:
    """ref: 'latest', 'latest_death', 'latest_win', 'previous', a run id (start time),
    a negative index ('-2' = second most recent), or a seed."""
    if not runs:
        return None
    ref = str(ref or "latest").strip().lower()
    solo = runs
    if ref in ("latest", "last", "most_recent"):
        return solo[-1]
    if ref == "previous":
        return solo[-2] if len(solo) > 1 else None
    if ref in ("latest_death", "last_death"):
        return next((r for r in reversed(solo) if r.outcome == "death"), None)
    if ref in ("latest_win", "last_win"):
        return next((r for r in reversed(solo) if r.outcome == "win"), None)
    if ref.lstrip("-").isdigit():
        n = int(ref)
        if n < 0 and -n <= len(solo):
            return solo[n]
        return next((r for r in solo if r.id == n), None)
    return next((r for r in solo if r.seed.lower() == ref or r.key.lower() == ref), None)


# ---------------------------------------------------------------- baselines
def peers(runs: list[Run], r: Run, min_n: int = 12) -> tuple[list[Run], str]:
    """Comparable runs: same character, solo, same ascension (widened to ±1 if too few)."""
    base = [x for x in runs if x.character == r.character and x.players == 1 and x.key != r.key and x.outcome != "abandoned"]
    same = [x for x in base if x.ascension == r.ascension]
    if len(same) >= min_n:
        return same, f"your other {len(same)} finished {pretty(r.character)} A{r.ascension} runs"
    near = [x for x in base if abs(x.ascension - r.ascension) <= 1]
    return near, f"your {len(near)} finished {pretty(r.character)} runs at A{r.ascension - 1}–A{r.ascension + 1}"


def encounter_stats(runs: list[Run], encounter: str, character: str | None = None,
                    ascension: int | None = None, exclude_key: str | None = None) -> dict:
    dmg, turns, deaths, n = [], [], 0, 0
    for x in runs:
        if character and x.character != character:
            continue
        if ascension is not None and x.ascension != ascension:
            continue
        if x.key == exclude_key:
            continue
        for i, f in enumerate(x.floors):
            if f.encounter == encounter:
                n += 1
                dmg.append(f.dmg)
                turns.append(f.turns)
                if x.outcome == "death" and i == len(x.floors) - 1:
                    deaths += 1
    return {"encounter": encounter, "name": pretty(encounter), "kind": encounter_kind(encounter), "fought": n,
            "avg_damage": round(mean(dmg), 1) if dmg else None, "median_damage": median(dmg) if dmg else None,
            "worst_damage": max(dmg) if dmg else None, "avg_turns": round(mean(turns), 1) if turns else None,
            "deaths": deaths, "death_rate": round(deaths / n, 3) if n else None}


def _boss_floor(r: Run, act: int) -> Floor | None:
    return next((f for f in r.floors if f.act == act and f.t == "B"), None)


def _act_floors(r: Run, act: int) -> list[Floor]:
    return [f for f in r.floors if f.act == act]


def _cleared_act(r: Run, act: int) -> bool:
    return r.outcome == "win" or r.act_reached > act


# ---------------------------------------------------------------- deck over time
def deck_at(r: Run, floor: int) -> list[dict]:
    """Best reconstruction of the deck as it was when entering `floor`.
    Uses final deck + removals/transforms with their floors. Upgrades are shown as of run end."""
    cards = [c for c in r.deck if (c.get("floor") or 0) < floor]
    for f in r.floors:
        if f.f < floor:
            continue
        for rid in f.removed:
            cards.append({"id": rid, "up": 0, "ench": "", "floor": 0, "later_removed": f.f})
        for orig, _new in f.transformed:
            cards.append({"id": orig, "up": 0, "ench": "", "floor": 0, "later_transformed": f.f})
    return cards


def deck_profile(cards: list[dict], kb: Knowledge) -> dict:
    types = Counter(kb.card_type(c["id"]) for c in cards)
    return {"size": len(cards), "basics": sum(1 for c in cards if _basic(c["id"])),
            "upgraded": sum(1 for c in cards if c.get("up")), "types": dict(types)}


# ---------------------------------------------------------------- roles and archetypes
# What the deck can do (roles: AoE, scaling, block, draw, ...) and which archetypes it's built around, from the card
# annotations in knowledge/ (annotations.py). Cards without an annotation fall back to a keyword heuristic over
# their text and are marked unannotated (*).
def _role_names(snap: dict, role: str, ann: Annotations) -> str:
    c = Counter(pretty(i) + ("" if ann.get(i) else "*") for i in snap["role_cards"][role])
    return ", ".join(f"{k}×{n}" if n > 1 else k for k, n in c.items())


def roles_line(snap: dict, ann: Annotations) -> str:
    """'Front-load 2 · AoE 1 (Thunderclap) · Scaling 2 (Inflame, Rupture*) · Block 4 · ...' (* = from card text)."""
    bits = []
    for r in ROLES:
        n = snap["roles"][r]
        if r in ("front_load", "block") or not n:
            bits.append(f"{ROLE_LABEL[r]} {n}")
        else:
            bits.append(f"{ROLE_LABEL[r]} {n} ({_role_names(snap, r, ann)})")
    return " · ".join(bits)


def archetypes_line(snap: dict) -> str:
    bits = []
    for v in snap["archetypes"].values():
        if v["state"] == "absent":
            continue
        ep = f"E{v['E']} P{v['P']}"
        if v["E_text"] or v["P_text"]:
            ep += f", {v['E_text'] + v['P_text']} from card text"
        sup = ""
        if v["state"] in ("committed", "half_built"):
            sup = "; support ok" if v["support_ok"] else "; support short: " + ", ".join(
                f"{ROLE_LABEL[r]} {have} of {need}" for r, (have, need) in v["support_short"].items())
        bits.append(f"{v['name']} {v['state']} ({ep}; committed at E{v['need'][0]} P{v['need'][1]}{sup})")
    return " · ".join(bits) or "none started"


def passed_roles(r: Run, before_floor: int, missing: list[str], kb: Knowledge, ann: Annotations) -> dict[str, list[str]]:
    """Cards offered as rewards (not shop stock) before `before_floor` that would have covered a missing role."""
    out: dict[str, list[str]] = {k: [] for k in missing}
    for f in r.floors:
        if f.f >= before_floor or f.t == "S":
            continue
        for c in f.cards_skipped:
            rs, annotated = ann.roles(c, kb)
            for k in missing:
                if k in rs:
                    out[k].append(f"{pretty(c)}{'' if annotated else '*'} (F{f.f})")
    return out


def _is_reward(f: Floor) -> bool:
    return f.t != "S" and bool(f.cards_picked or f.cards_skipped)


def archetype_report(r: Run, kb: Knowledge, ann: Annotations) -> dict:
    """knowledge/SCHEMA.md section 3 for one run. Snapshots at each card reward and shop (deck after the floor) and
    each boss (deck entering it). Commit floors and pivots are tracked floor by floor, so event cards count too."""
    snaps: list[dict] = []
    commit: dict[str, int] = {}
    pivots: list[tuple[int, str, str]] = []
    last_primary = None
    for f in r.floors:
        if f.t == "B":
            cards = deck_at(r, f.f)
            snaps.append({"floor": f.f, "act": f.act, "event": "boss", "encounter": f.encounter, "cards": cards,
                          **ann.snapshot(cards, r.character, kb, last_primary)})
        cards = deck_at(r, f.f + 1)
        after = ann.snapshot(cards, r.character, kb, last_primary)
        for k, v in after["archetypes"].items():
            if v["state"] == "committed" and k not in commit:
                commit[k] = f.f
        if after["primary"]:
            if last_primary and after["primary"] != last_primary:
                pivots.append((f.f, last_primary, after["primary"]))
            last_primary = after["primary"]
        if f.t == "S" or _is_reward(f):
            snaps.append({"floor": f.f, "act": f.act, "event": "shop" if f.t == "S" else "card reward",
                          "picked": f.cards_picked + f.cards_bought, "cards": cards, **after})
    bosses = [s for s in snaps if s["event"] == "boss"]
    half = [(s, k, v) for s in bosses for k, v in s["archetypes"].items()
            if v["state"] == "half_built" or (v["state"] == "committed" and not v["support_ok"])]
    final = bosses[-1] if bosses else None
    orphans = ann.orphans(final, final["cards"], kb) if final else []
    # the cards the report leans on: everything non-basic in a boss deck or the final deck
    used = {c["id"] for s in bosses for c in s["cards"]} | {c["id"] for c in r.deck}
    used = sorted(i for i in used if not is_basic(i) and kb.card_type(i) not in ("Curse", "Status"))
    annotated = [i for i in used if ann.get(i)]
    states = {i: ann.review_state(i, r.build) for i in annotated}
    return {"has_archetypes": bool(ann.archetype_doc(r.character)), "snapshots": snaps, "bosses": bosses,
            "primary": [(s["act"], s["floor"], s["primary"]) for s in bosses], "commit_floor": commit,
            "pivots": pivots, "half_built_at": half, "orphans": orphans, "final": final,
            "confidence": {"used": used, "annotated": annotated,
                           "draft": [i for i in annotated if states[i]["status"] != "reviewed"],
                           "stale": [i for i in annotated if states[i]["fresh"] == "stale"],
                           "unchecked": [i for i in annotated if states[i]["fresh"] == "unchecked"],
                           "unannotated": [i for i in used if not ann.get(i)]}}


def _arch_name(r: Run, ann: Annotations, aid: str | None) -> str:
    if not aid:
        return "none"
    doc = ann.archetype_doc(r.character) or {}
    return next((a.get("name", aid) for a in doc.get("archetypes") or [] if a.get("id") == aid), aid)


def archetype_lines(r: Run, rep: dict, ann: Annotations) -> list[str]:
    if not rep["has_archetypes"]:
        return [f"- No archetype definitions for {pretty(r.character)} yet "
                f"(knowledge/{r.character.lower()}/archetypes.yaml); the Synergies section has text-based hints."]
    out = ["- Primary archetype at each boss: " + (" · ".join(
        f"Act {a} (F{fl}) {_arch_name(r, ann, p)}" for a, fl, p in rep["primary"]) or "no boss reached")]
    out.append("- First committed: " + (", ".join(f"{_arch_name(r, ann, k)} F{fl}" for k, fl in
                                                 sorted(rep["commit_floor"].items(), key=lambda kv: kv[1])) or "never"))
    if rep["pivots"]:
        out.append("- Pivots (primary archetype changed): " + ", ".join(
            f"F{fl} {_arch_name(r, ann, a)} → {_arch_name(r, ann, b)}" for fl, a, b in rep["pivots"]))
    for s, _k, v in rep["half_built_at"]:
        short = ", ".join(f"{ROLE_LABEL[x]} {h} of {n}" for x, (h, n) in v["support_short"].items())
        counts = f"E{v['E']} P{v['P']}; committed at E{v['need'][0]} P{v['need'][1]}"
        if v["state"] == "half_built":
            line = f"{v['name']} half_built ({counts}): payoffs without enough enablers"
        else:
            line = f"{v['name']} committed ({counts}) but support short: {short}"
        out.append(f"- Act {s['act']} boss (F{s['floor']}): {line}"
                   + (f"; support short: {short}" if short and v["state"] == "half_built" else ""))
    if rep["orphans"]:
        out.append(f"- Orphans at the Act {rep['final']['act']} boss (feed a mechanic no archetype in the deck uses, "
                   "add no role the deck lacks): " + ", ".join(f"{pretty(i)} ({', '.join(t)})" for i, t in rep["orphans"]))
    return out


def confidence_line(rep: dict) -> str:
    c = rep["confidence"]

    def names(ids: list[str]) -> str:
        return f": {_names(ids)}" if ids and len(ids) <= 8 else ""
    return (f"Of {len(c['used'])} non-basic cards in the boss decks and final deck: {len(c['annotated'])} annotated "
            f"({len(c['draft'])} draft{names(c['draft'])}; {len(c['stale'])} stale{names(c['stale'])}; "
            f"{len(c['unchecked'])} not checked against a game build), "
            f"{len(c['unannotated'])} unannotated (roles from card text, marked *).")


def snapshots_table(r: Run, rep: dict, ann: Annotations) -> str:
    """Every deck snapshot, for the get_deck_snapshots tool."""
    out = [f"# Deck snapshots: run {r.id}, {pretty(r.character)} A{r.ascension}, {outcome_line(r)}",
           "Roles from card annotations (knowledge/); cards without one are counted from their text. Strikes, Defends "
           "and curses excluded. Card rewards and shops show the deck after the floor; bosses the deck entering it. "
           "Archetypes: state (E enablers, P payoffs).", ""]
    out += archetype_lines(r, rep, ann)
    out.append("")
    out.append("| Floor | Event | Picked | Deck | " + " | ".join(ROLE_LABEL[x] for x in ROLES) + " | Archetypes |")
    out.append("|---|---|---|---|" + "---|" * len(ROLES) + "---|")
    for s in rep["snapshots"]:
        ev = s["event"] + (f" ({pretty(s['encounter'])})" if s.get("encounter") else "")
        arch = "; ".join(f"{k} {v['state']} E{v['E']}P{v['P']}"
                         + (" support short" if v["state"] == "committed" and not v["support_ok"] else "")
                         for k, v in s["archetypes"].items() if v["state"] != "absent") or "—"
        out.append(f"| F{s['floor']} | {ev} | {_names(s.get('picked') or []) or '—'} | {s['size']} | "
                   + " | ".join(str(s["roles"][x]) for x in ROLES) + f" | {arch} |")
    out.append("\n**Knowledge confidence:** " + confidence_line(rep))
    return "\n".join(out)


def synergy_check(cards: list[dict], relic_ids: list[str], kb: Knowledge) -> dict[str, dict[str, list[str]]]:
    """Per mechanic: which deck cards/relics feed it and which pay it off (tags from the game-data builder)."""
    out: dict[str, dict[str, list[str]]] = {}
    items = [("card", c["id"]) for c in cards if c["id"] != "ASCENDERS_BANE"] + [("relic", i) for i in relic_ids]
    for kind, i in items:
        e = kb.get(kind, i)
        if not e:
            continue
        for role, key in (("feeds", "enables"), ("payoffs", "rewards")):
            for m in e.get(key, []):
                if m in MECHANICS:
                    v = out.setdefault(m, {"feeds": [], "payoffs": [], "payoff_cards": []})
                    v[role].append(i)
                    if role == "payoffs" and kind == "card":
                        v["payoff_cards"].append(i)
    # a mechanic matters when something pays it off, or when several things feed one that needs a payoff
    return {m: v for m, v in sorted(out.items(), key=lambda kv: -(len(kv[1]["feeds"]) + 3 * len(kv[1]["payoffs"])))
            if v["payoffs"] or (len(v["feeds"]) >= 3 and m in PAYOFF_MATTERS)}


def synergy_line(syn: dict) -> str:
    def names(ids: list[str]) -> str:
        c = Counter(pretty(i) for i in ids)
        return ", ".join(f"{k}×{n}" if n > 1 else k for k, n in c.items())
    return " · ".join(f"{mech_label(m)}: feeds {len(v['feeds'])}"
                      + (f" ({names(v['feeds'])})" if m != "strike" and v["feeds"] else "")
                      + f", payoffs {len(v['payoffs'])}" + (f" ({names(v['payoffs'])})" if v["payoffs"] else "")
                      for m, v in syn.items())


def passed_payoffs(r: Run, before_floor: int, syn: dict, kb: Knowledge) -> dict[str, list[str]]:
    """Card rewards (not shop stock) before `before_floor` that would have paid off a mechanic the deck feeds."""
    fed = [m for m, v in syn.items() if len(v["feeds"]) >= 2 and m in PAYOFF_MATTERS]
    out: dict[str, list[str]] = {}
    for f in r.floors:
        if f.f >= before_floor or f.t == "S":
            continue
        for c in f.cards_skipped:
            for m in (kb.get("card", c) or {}).get("rewards", []):
                if m in fed:
                    out.setdefault(m, []).append(f"{pretty(c)} (F{f.f})")
    return out


def synergy_warnings(syn: dict, passed: dict[str, list[str]]) -> list[str]:
    w = []
    for m, v in syn.items():
        if len(v["feeds"]) >= 3 and not v["payoffs"] and m in NEEDS_PAYOFF:
            w.append(f"{mech_label(m)} fed by {len(v['feeds'])} cards/relics but nothing in the deck rewards it"
                     + (f"; passed payoffs: {', '.join(passed[m])}" if passed.get(m) else ""))
        elif v["payoff_cards"] and len(v["feeds"]) <= 1 and m not in ("strike", "strength"):
            # a payoff card (not a free relic) drawn into a deck that barely feeds it
            w.append(f"{mech_label(m)} payoff ({', '.join(pretty(i) for i in v['payoff_cards'])}) with little feeding it")
        elif passed.get(m):
            w.append(f"{mech_label(m)}: also passed payoffs {', '.join(passed[m])}")
    return w


# ---------------------------------------------------------------- the digest
def _names(ids: list[str]) -> str:
    return ", ".join(pretty(i) for i in ids)


def floor_line(f: Floor, enc_avg: dict[str, dict]) -> str:
    parts = [f"F{f.f:<2} A{f.act} {f.t}"]
    what = []
    if f.t == "A" and f.ancient_pick:
        others = [o for o in f.ancient_options if o != f.ancient_pick]
        what.append(f"{pretty(f.models[0]) if f.models else 'Ancient'}: took {pretty(f.ancient_pick)}"
                    + (f" over {_names(others)}" if others else ""))
    elif f.encounter:
        e = enc_avg.get(f.encounter)
        cmp_ = ""
        if e and e["fought"] >= 3 and e["avg_damage"] is not None:
            cmp_ = f" (your avg {e['avg_damage']:g}, n={e['fought']})"
        pre = ""
        if f.t == "?":
            pre = f"event→fight {pretty(f.models[0])}: " if len(f.models) > 1 else "event fight: "
        what.append(f"{pre}{pretty(f.encounter)} −{f.dmg}{cmp_}, {f.turns} turns")
    elif f.t == "?":
        what.append(f"{pretty(f.models[0]) if f.models else 'Event'}" + (f": {' → '.join(f.events)}" if f.events else ""))
        if f.dmg:
            what.append(f"−{f.dmg} HP")
    elif f.t == "R":
        pct = round(100 * (f.hp_before or 0) / f.max_hp) if f.max_hp else 0
        what.append(f"rest site at {f.hp_before}/{f.max_hp} ({pct}%): {f.rest.lower() or 'nothing recorded'}")
    elif f.t == "S":
        what.append(f"shop, spent {f.gold_spent}g" if f.gold_spent else "shop, bought nothing")
    elif f.t == "T":
        what.append("treasure")
    parts.append("; ".join(what) if what else ROOM_NAME[f.t])
    parts.append(f"HP {f.hp}/{f.max_hp}" + (f" (+{f.heal})" if f.heal and f.t not in ("R", "A") else "") + f", {f.gold}g")
    extra = []
    if f.t == "S":
        bought = [g for g in f.gained_other]
        if bought:
            extra.append(f"bought cards {_names(bought)}")
        if f.cards_skipped:
            extra.append(f"other cards in stock: {_names(f.cards_skipped)}")
    elif f.cards_picked or f.cards_skipped:
        if f.cards_picked:
            extra.append(f"took {_names(f.cards_picked)}" + (f" over {_names(f.cards_skipped)}" if f.cards_skipped else ""))
        else:
            extra.append(f"skipped cards {_names(f.cards_skipped)}")
    gained = [g for g in f.gained_other if g not in f.cards_picked]
    if gained and f.t != "S":
        extra.append(f"gained {_names(gained)}")
    if f.relics_picked and f.t != "S":
        extra.append(f"relic {_names(f.relics_picked)}" + (f" over {_names(f.relics_skipped)}" if f.relics_skipped else ""))
    if f.t == "S" and f.relics_skipped:
        extra.append(f"other relics in stock: {_names(f.relics_skipped)}")
    if f.relics_bought:
        extra.append(f"bought relic {_names(f.relics_bought)}")
    if f.cards_bought:
        extra.append(f"bought card {_names(f.cards_bought)}")
    if f.potions_bought:
        extra.append(f"bought potion {_names(f.potions_bought)}")
    if f.upgraded:
        extra.append(f"upgraded {_names(f.upgraded)}")
    if f.removed:
        extra.append(f"removed {_names(f.removed)}")
    if f.transformed:
        extra.append("transformed " + ", ".join(f"{pretty(a)}→{pretty(b)}" for a, b in f.transformed))
    if f.enchanted:
        extra.append("enchanted " + ", ".join(f"{pretty(c)} with {pretty(e)}" for c, e in f.enchanted))
    if f.potions_picked:
        extra.append(f"potion {_names(f.potions_picked)}")
    if f.potions_used:
        extra.append(f"drank {_names(f.potions_used)}")
    if f.potions_discarded:
        extra.append(f"discarded {_names(f.potions_discarded)}")
    if f.max_hp_gain or f.max_hp_loss:
        extra.append(f"max HP {'+' + str(f.max_hp_gain) if f.max_hp_gain else ''}{' −' + str(f.max_hp_loss) if f.max_hp_loss else ''}")
    if f.gold_lost:
        extra.append(f"lost {f.gold_lost}g")
    line = " | ".join(parts)
    return line + ("  ▸ " + "; ".join(extra) if extra else "")


def digest(runs: list[Run], r: Run, kb: Knowledge, glossary: str = "deck", ann: Annotations | None = None) -> str:
    ann = ann or Annotations()
    ps, peer_desc = peers(runs, r)
    out: list[str] = []
    out.append(f"# Run {r.id}: {pretty(r.character)} A{r.ascension}, {outcome_line(r)}")
    out.append(f"{fmt_date(r.start)} · version {r.build} · {fmt_dur(r.duration)} on the clock · acts {' → '.join(pretty(a) for a in r.acts)} · seed {r.seed}"
               + (f" · co-op ({r.players} players)" if r.players > 1 else ""))
    out.append(f"Baselines below compare with {peer_desc}.")
    ch = kb.get("character", r.character)
    if ch:
        out.append(f"Character (game data): {ch.get('text', '')}")

    # --- death / ending
    last = r.last
    if r.outcome == "death" and last:
        es = encounter_stats(runs, last.encounter, r.character, exclude_key=r.key) if last.encounter else None
        out.append("\n## How it ended")
        out.append(f"- Final room: floor {last.f}, Act {last.act} {ROOM_NAME[last.t]}"
                   + (f", {pretty(last.encounter)} ({encounter_kind(last.encounter)})" if last.encounter else "")
                   + f". Entered at {last.hp_before}/{last.max_hp} HP, fight lasted {last.turns} turns.")
        if es and es["fought"]:
            out.append(f"- Your history vs {es['name']} ({pretty(r.character)}, all ascensions): fought {es['fought']}×, "
                       f"avg −{es['avg_damage']} HP, worst −{es['worst_damage']}, killed you {es['deaths']}× "
                       f"({round(100 * (es['death_rate'] or 0))}%).")
        if r.potions_held:
            out.append(f"- Potions still held at death: {_names(r.potions_held)}.")
        out.append(f"- Gold at death: {last.gold}g.")

    # --- key numbers vs baseline
    out.append("\n## This run vs your baseline")
    out.append("| Measure | This run | Your typical |")
    out.append("|---|---|---|")
    for act in range(1, r.act_reached + 1):
        fl = _act_floors(r, act)
        reached_end = _cleared_act(r, act) or (last and last.act == act and last.t == "B")
        p_act = [x for x in ps if _cleared_act(x, act)]
        dm = sum(f.dmg for f in fl)
        p_dm = [sum(f.dmg for f in _act_floors(x, act)) for x in p_act]
        el = sum(1 for f in fl if f.t == "E")
        p_el = [sum(1 for f in _act_floors(x, act) if f.t == "E") for x in p_act]
        note = "" if reached_end else " (act not finished)"
        if p_dm:
            out.append(f"| Act {act} damage taken{note} | {dm} | {round(mean(p_dm))} in runs that cleared act {act} |")
            out.append(f"| Act {act} elites fought{note} | {el} | {mean(p_el):.1f} in runs that cleared act {act} |")
        bf = _boss_floor(r, act)
        if bf:
            p_hp = [(_boss_floor(x, act).hp_before / _boss_floor(x, act).max_hp) for x in ps
                    if _boss_floor(x, act) and _boss_floor(x, act).max_hp]
            p_hp_w = [(_boss_floor(x, act).hp_before / _boss_floor(x, act).max_hp) for x in p_act
                      if _boss_floor(x, act) and _boss_floor(x, act).max_hp]
            mine = round(100 * bf.hp_before / bf.max_hp) if bf.max_hp else 0
            out.append(f"| HP entering Act {act} boss ({pretty(bf.encounter)}) | {bf.hp_before}/{bf.max_hp} ({mine}%) | "
                       f"{round(100 * mean(p_hp)) if p_hp else '—'}% overall, {round(100 * mean(p_hp_w)) if p_hp_w else '—'}% when you won that fight |")
            dk = deck_profile(deck_at(r, bf.f), kb)
            p_dk = [deck_profile(deck_at(x, _boss_floor(x, act).f), kb) for x in p_act if _boss_floor(x, act)]
            if p_dk:
                out.append(f"| Deck size at Act {act} boss | {dk['size']} ({dk['basics']} Strikes/Defends) | "
                           f"{mean(d['size'] for d in p_dk):.0f} ({mean(d['basics'] for d in p_dk):.0f} basics) when you cleared it |")
    is_reward = lambda f: f.t != "S" and (f.cards_picked or f.cards_skipped)
    offers = [f for f in r.floors if is_reward(f)]
    skips = sum(1 for f in offers if not f.cards_picked)
    p_off = [(sum(1 for f in x.floors if is_reward(f) and not f.cards_picked),
              sum(1 for f in x.floors if is_reward(f))) for x in ps]
    p_rate = sum(a for a, _ in p_off) / max(1, sum(b for _, b in p_off))
    out.append(f"| Card rewards skipped | {skips} of {len(offers)} ({round(100 * skips / max(1, len(offers)))}%) | {round(100 * p_rate)}% |")
    rem = sum(len(f.removed) for f in r.floors)
    per_floor = rem / max(1, r.floors_reached)
    p_rem = [sum(len(f.removed) for f in x.floors) / max(1, x.floors_reached) for x in ps]
    out.append(f"| Cards removed | {rem} ({per_floor * 17:.1f} per 17 floors) | {mean(p_rem) * 17:.1f} per 17 floors |" if p_rem else f"| Cards removed | {rem} | — |")
    used = sum(len(f.potions_used) for f in r.floors)
    p_used = [sum(len(f.potions_used) for f in x.floors) / max(1, x.floors_reached) for x in ps]
    out.append(f"| Potions drunk | {used} ({used / max(1, r.floors_reached) * 17:.1f} per 17 floors) | {mean(p_used) * 17:.1f} per 17 floors |" if p_used else f"| Potions drunk | {used} | — |")
    rests = [f for f in r.floors if f.t == "R"]
    if rests:
        p_r = [f for x in ps for f in x.floors if f.t == "R"]
        p_smith = sum(f.rest == "SMITH" for f in p_r) / max(1, len(p_r))
        p_heal_hp = [f.hp_before / f.max_hp for f in p_r if f.rest == "HEAL" and f.max_hp]
        heal_hp = [f.hp_before / f.max_hp for f in rests if f.rest == "HEAL" and f.max_hp]
        out.append(f"| Rest sites: rest / smith / other | {sum(f.rest == 'HEAL' for f in rests)} / {sum(f.rest == 'SMITH' for f in rests)} / "
                   f"{sum(f.rest not in ('HEAL', 'SMITH') for f in rests)} | you smith at {round(100 * p_smith)}% of rest sites |")
        if heal_hp and p_heal_hp:
            out.append(f"| Average HP when choosing to rest | {round(100 * mean(heal_hp))}% | {round(100 * mean(p_heal_hp))}% |")

    # --- fights that went badly compared with history
    enc_avg: dict[str, dict] = {}
    for f in r.floors:
        if f.encounter and f.encounter not in enc_avg:
            enc_avg[f.encounter] = encounter_stats(runs, f.encounter, r.character, exclude_key=r.key)
    bad = [f for f in r.floors if f.encounter and enc_avg[f.encounter]["fought"] >= 3
           and f.dmg >= max(10, 1.5 * (enc_avg[f.encounter]["avg_damage"] or 0))]
    if bad:
        out.append("\n## Fights well above your usual damage")
        for f in bad:
            e = enc_avg[f.encounter]
            out.append(f"- F{f.f} {pretty(f.encounter)}: −{f.dmg} vs your avg {e['avg_damage']:g} (n={e['fought']}), {f.turns} turns")

    # --- what the deciding fights' enemies do (game data, at this run's ascension)
    deciding = [f for f in r.floors if f.t == "B"] + bad
    if r.outcome == "death" and last and last.encounter:
        deciding = [last] + deciding
    enemy_lines, seen_enc = [], set()
    for f in deciding:
        enc = kb.get("encounter", strip_prefix(f.encounter)) if f.encounter else None
        if not enc or f.encounter in seen_enc:
            continue
        seen_enc.add(f.encounter)
        mons = [kb.get("monster", m) for m in enc.get("monsters") or []]
        why = ("killed you" if (r.outcome == "death" and last and f.f == last.f)
               else "boss" if f.t == "B" else "well above your usual damage")
        label = enc.get("room") or "fight"
        label += "" if why == label else f", {why}"
        enemy_lines.append(f"- F{f.f} {enc['name']} ({label}): "
                           + (" | ".join(monster_line(m, r.ascension) for m in mons if m) or enc.get("text", "")))
    if enemy_lines:
        out.append(f"\n## Enemies in the deciding fights (game data, at A{r.ascension})")
        out.append("HP and move numbers from the game files at this run's ascension. Intents and powers are what each "
                   "move does; the order and frequency of moves aren't shown, and some values aren't readable.")
        out += enemy_lines

    # --- roles and archetypes at each boss (knowledge/ annotations; text heuristic for unannotated cards)
    ann.refresh()
    rep = archetype_report(r, kb, ann)
    out.append("\n## Deck roles and archetypes at each boss")
    out.append("Role counts come from card annotations (knowledge/); cards marked * have none and are counted from "
               "their text. Strikes/Defends and curses excluded; a card can count for several roles. Archetype states "
               "are computed: absent, forming, committed (enablers E and payoffs P at the archetype's thresholds), "
               "half_built (payoffs without enough enablers). Full per-reward timeline: get_deck_snapshots.")
    for s in rep["bosses"]:
        out.append(f"- Act {s['act']} boss (F{s['floor']}), {s['size']} cards: {roles_line(s, ann)}")
        if rep["has_archetypes"]:
            out.append(f"  - Archetypes: {archetypes_line(s)}")
        missing = [k for k in ("aoe", "draw", "scaling") if not s["roles"][k]]
        for k, offered in passed_roles(r, s["floor"], missing, kb, ann).items():
            if offered:
                out.append(f"  - No {ROLE_LABEL[k]} in deck, but passed: {', '.join(offered)}")
    if r.outcome == "death" and last and (not _boss_floor(r, last.act) or _boss_floor(r, last.act).f != last.f):
        snap = ann.snapshot(r.deck, r.character, kb)
        out.append(f"- At death (F{last.f}), {snap['size']} cards: {roles_line(snap, ann)}")
        if rep["has_archetypes"]:
            out.append(f"  - Archetypes: {archetypes_line(snap)}")
    out.append("\n## Archetype timeline")
    out += archetype_lines(r, rep, ann)
    out.append("\n## Knowledge confidence")
    out.append("- " + confidence_line(rep))
    out.append("- Draft annotations haven't been reviewed by a human; stale ones were checked on an older build whose "
               "card text differs. Caveat claims that rest on them.")

    # --- synergies: what feeds what
    syn_lines = []
    points = [(f"Act {a} boss (F{_boss_floor(r, a).f})", _boss_floor(r, a).f) for a in range(1, r.act_reached + 1) if _boss_floor(r, a)]
    if r.outcome == "death" and last and all(f != last.f for _, f in points):
        points.append((f"At death (F{last.f})", last.f + 1))
    for name, fl in points:
        syn = synergy_check(deck_at(r, fl), [x["id"] for x in r.relics if x["floor"] <= fl], kb)
        if syn:
            syn_lines.append(f"- {name}: {synergy_line(syn)}")
            syn_lines += [f"  - {w}" for w in synergy_warnings(syn, passed_payoffs(r, fl, syn, kb))]
    if syn_lines:
        out.append("\n## Synergies at each boss (what feeds what)")
        out.append("From card and relic text: 'feeds' make a mechanic happen, 'payoffs' reward it. Hints, not rules.")
        out += syn_lines

    # --- decks at each boss
    out.append("\n## Deck at each boss (reconstructed)")
    for act in range(1, r.act_reached + 1):
        bf = _boss_floor(r, act)
        if not bf:
            continue
        cards = deck_at(r, bf.f)
        dk = deck_profile(cards, kb)
        c = Counter(pretty(x["id"]) for x in cards)
        out.append(f"- Act {act} boss (F{bf.f}), {dk['size']} cards, types {dk['types']}: "
                   + ", ".join(f"{n}×{k}" if n > 1 else k for k, n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))))

    # --- final state
    out.append("\n## Final deck, relics, potions")
    fc = Counter((pretty(c["id"]) + ("+" * min(c["up"], 1)) + (f" [{pretty(c['ench'])}]" if c["ench"] else "")) for c in r.deck)
    out.append(f"- Deck ({len(r.deck)}): " + ", ".join(f"{n}×{k}" if n > 1 else k for k, n in sorted(fc.items(), key=lambda kv: (-kv[1], kv[0]))))
    out.append("- Relics (floor found): " + ", ".join(f"{pretty(x['id'])} (F{x['floor']})" for x in r.relics))
    out.append("- Potions held at end: " + (_names(r.potions_held) or "none"))

    # --- floor log
    out.append("\n## Floor log")
    out.append("Glyphs: H hallway, E elite, B boss, ? event, R rest, S shop, T treasure, A ancient. −N = HP lost on that floor.")
    out.append("```")
    act = 0
    for f in r.floors:
        if f.act != act:
            act = f.act
            out.append(f"-- Act {act}: {pretty(r.acts[act - 1]) if act <= len(r.acts) else ''}")
        out.append(floor_line(f, enc_avg))
    out.append("```")

    # --- glossary
    if glossary != "none":
        out.append("\n## What things do (game data may be from an older version)")
        seen: list[tuple[str, str]] = []
        def add(kind: str, i: str) -> None:
            if (kind, i) not in seen:
                seen.append((kind, i))
        for c in r.deck:
            add("card", c["id"])
        for x in r.relics:
            add("relic", x["id"])
        for f in r.floors:
            for p in f.potions_used + f.potions_picked:
                add("potion", p)
            if glossary == "full":
                for c in f.cards_picked + f.cards_skipped:
                    add("card", c)
        for p in r.potions_held:
            add("potion", p)
        for kind in ("card", "relic", "potion"):
            items = [i for k, i in seen if k == kind]
            if items:
                out.append(f"**{kind.title()}s**")
                out.extend(f"- {kb.describe(kind, i)}" for i in items)
        # keywords and powers the deck's text mentions (Vulnerable, Plating, Exhaust, ...)
        terms: list[tuple[str, dict]] = []
        for kind, i in seen:
            for ref in (kb.get(kind, i) or {}).get("refs", []):
                forms = [ref, ref.removesuffix("ed"), ref.removesuffix("s")]          # "Exhausted" -> Exhaust
                e = next((x for f in forms for x in (kb.get("keyword", f), kb.get("power", f)) if x), None)
                if e and e["name"] not in [t for t, _ in terms]:
                    terms.append((e["name"], e))
        if terms:
            out.append("**Keywords & powers**")
            out.extend(f"- {n}: {e.get('text', '').strip()}" for n, e in sorted(terms))
    return "\n".join(out)


# ---------------------------------------------------------------- cross-run summaries
def run_row(r: Run) -> str:
    return (f"{r.id} | {datetime.fromtimestamp(r.start):%d %b %Y %H:%M} | {pretty(r.character)} A{r.ascension} | {r.outcome} | "
            f"floor {r.floors_reached} | {pretty(r.killer) or '—'} | {r.build}")


def player_summary(runs: list[Run], character: str | None, ascension: int | None, last_n: int | None,
                   kb: Knowledge | None = None, ann: Annotations | None = None) -> str:
    sel = [r for r in runs if r.players == 1 and (not character or r.character == character.upper())
           and (ascension is None or r.ascension == ascension)]
    if last_n:
        sel = sel[-last_n:]
    if not sel:
        return "No runs match."
    fin = [r for r in sel if r.outcome != "abandoned"]
    wins = [r for r in sel if r.outcome == "win"]
    out = [f"# {len(sel)} runs ({pretty(character) if character else 'all characters'}"
           f"{f', A{ascension}' if ascension is not None else ''}), {fmt_date(sel[0].start)[4:15]} to {fmt_date(sel[-1].start)[4:15]}",
           f"- Wins {len(wins)} of {len(fin)} finished ({round(100 * len(wins) / max(1, len(fin)))}%), {len(sel) - len(fin)} abandoned",
           f"- Median floor {median(r.floors_reached for r in sel)}"]
    for act in (1, 2, 3):
        reach = [r for r in fin if _boss_floor(r, act)]
        clear = [r for r in fin if _cleared_act(r, act)]
        out.append(f"- Act {act} boss reached {len(reach)} ({round(100 * len(reach) / max(1, len(fin)))}%), cleared {len(clear)} ({round(100 * len(clear) / max(1, len(fin)))}%)")
    deaths = [r for r in sel if r.outcome == "death"]
    by_kind = Counter(r.last.t for r in deaths if r.last)
    out.append("- Deaths by room: " + ", ".join(f"{ROOM_NAME[k]} {v}" for k, v in by_kind.most_common()))
    out.append("- Top killers: " + ", ".join(f"{pretty(k)} {v}" for k, v in Counter(r.killer for r in deaths).most_common(8)))
    picks, offers = Counter(), Counter()
    for r in sel:
        for f in r.floors:
            if f.t == "S":
                continue
            for c in f.cards_picked + f.cards_skipped:
                offers[c] += 1
            for c in f.cards_picked:
                picks[c] += 1
    top = sorted((c for c in offers if offers[c] >= 5), key=lambda c: -picks[c] / offers[c])[:10]
    out.append("- Cards you take most often (≥5 offers): " + ", ".join(f"{pretty(c)} {picks[c]}/{offers[c]}" for c in top))
    never = sorted((c for c in offers if offers[c] >= 6 and picks[c] == 0), key=lambda c: -offers[c])[:10]
    if never:
        out.append("- Offered often, never taken: " + ", ".join(f"{pretty(c)} ({offers[c]})" for c in never))
    rest_heal = [f.hp_before / f.max_hp for r in sel for f in r.floors if f.t == "R" and f.rest == "HEAL" and f.max_hp]
    rest_smith = [f.hp_before / f.max_hp for r in sel for f in r.floors if f.t == "R" and f.rest == "SMITH" and f.max_hp]
    if rest_heal or rest_smith:
        out.append(f"- Rest sites: rested {len(rest_heal)}× (avg HP {round(100 * mean(rest_heal)) if rest_heal else '—'}%), "
                   f"smithed {len(rest_smith)}× (avg HP {round(100 * mean(rest_smith)) if rest_smith else '—'}%)")
    # four problems at the Act 1 and Act 2 bosses vs clearing that act
    if kb is not None:
        ann = ann or Annotations()
        for act in (1, 2):
            rows = []
            for r in fin:
                bf = _boss_floor(r, act)
                if bf:
                    snap = ann.snapshot(deck_at(r, bf.f), r.character, kb)
                    rows.append((snap["roles"]["aoe"], snap["roles"]["draw"], _cleared_act(r, act)))
            if len(rows) >= 8:
                def rate(sub):
                    return f"{round(100 * sum(c for *_, c in sub) / len(sub))}% of {len(sub)}" if sub else "—"
                out.append(f"- Act {act} boss, beat it: with AoE {rate([x for x in rows if x[0]])}, without {rate([x for x in rows if not x[0]])}; "
                           f"with draw {rate([x for x in rows if x[1]])}, without {rate([x for x in rows if not x[1]])}")
    held = [len(r.potions_held) for r in deaths]
    if held:
        out.append(f"- Potions still held at death: avg {mean(held):.1f}; died holding at least one in {sum(1 for h in held if h)} of {len(held)} deaths")
    return "\n".join(out)


def climb(runs: list[Run], character: str) -> str:
    sel = [r for r in runs if r.character == character.upper() and r.players == 1]
    if not sel:
        return "No runs for that character."
    out = ["| Asc | Tries | Deaths | Abandoned | First try | Won | Won on |", "|---|---|---|---|---|---|---|"]
    for a in sorted({r.ascension for r in sel}):
        at = [r for r in sel if r.ascension == a]
        win = next((r for r in at if r.outcome == "win"), None)
        tries = [r for r in at if not win or r.start <= win.start]
        c = Counter(r.outcome for r in tries)
        out.append(f"| A{a} | {len(tries)} | {c['death']} | {c['abandoned']} | {fmt_date(tries[0].start)[4:15]} | "
                   f"{fmt_date(win.start)[4:15] if win else 'not yet'} | {win.build if win else '—'} |")
    return "\n".join(out)


def versions(runs: list[Run]) -> str:
    by = defaultdict(list)
    for r in runs:
        by[r.build].append(r)
    key = lambda b: [int(x) for x in b.lstrip("v").split(".") if x.isdigit()]
    out = ["| Version | Runs | Wins | First played | Last played | Ascensions |", "|---|---|---|---|---|---|"]
    for b in sorted(by, key=key, reverse=True):
        rs = by[b]
        out.append(f"| {b} | {len(rs)} | {sum(r.outcome == 'win' for r in rs)} | {fmt_date(rs[0].start)[4:15]} | "
                   f"{fmt_date(rs[-1].start)[4:15]} | A{min(r.ascension for r in rs)}–A{max(r.ascension for r in rs)} |")
    return "\n".join(out)
