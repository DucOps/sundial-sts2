"""Card annotations and archetypes from the knowledge layer (knowledge/, spec in knowledge/SCHEMA.md).

Turns a deck into facts the analyst can cite instead of inferring them:
  - role counts (front_load, aoe, scaling, block, draw, ...) from each card's annotation, falling back to a keyword
    heuristic over the card's text for cards nobody has annotated yet (those are reported as unannotated);
  - per archetype: enablers E, payoffs P, state (absent / forming / committed / half_built) and support_ok;
  - per card: review status and staleness (the game text changed since the build the annotation was checked on).

The per-run timeline (commit floors, pivots, ...) is in analysis.py, which knows how to rebuild a deck at a floor.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import yaml

from .knowledge import Knowledge, norm
from .store import data_home

ROLES = ("front_load", "aoe", "scaling", "block", "draw", "energy", "debuff", "sustain", "card_gen", "deck_thin")
ROLE_LABEL = {"front_load": "Front-load", "aoe": "AoE", "scaling": "Scaling", "block": "Block", "draw": "Draw",
              "energy": "Energy", "debuff": "Debuff", "sustain": "Sustain", "card_gen": "Card gen",
              "deck_thin": "Deck thin"}
STATES = ("absent", "forming", "committed", "half_built")

# The old keyword heuristic, used only for cards without an annotation. It reads the card's text, so it can't
# tell a one-off from a lasting effect as well as an annotation can; results are marked as unannotated.
_TEXT_ROLES = {
    "aoe": re.compile(r"ALL enemies"),
    "scaling": re.compile(r"[Gg]ain \d+ (Strength|Dexterity|Focus)|Poison|Doom|Forge|[Pp]ermanently|[Ee]very turn"
                          r"|[Aa]t the start of your turn"),
    "block": re.compile(r"\bBlock\b|Plating|Intangible"),
    "draw": re.compile(r"\b[Dd]raws? (?!Pile)"),
    "energy": re.compile(r"[Ee]nergy|Gain \[icon amount missing\]"),
    "debuff": re.compile(r"\bWeak\b|\bVulnerable\b|[Ll]oses? \d+ Strength"),
}


def is_basic(card_id: str) -> bool:
    """Strike / Defend (any character)."""
    return card_id.split("_")[0] in ("STRIKE", "DEFEND") and card_id.count("_") <= 1


def text_roles(card_id: str, kb: Knowledge) -> set[str]:
    e = kb.get("card", card_id)
    if not e:
        return set()
    text = e.get("text") or ""
    out = {k for k, rx in _TEXT_ROLES.items() if rx.search(text)}
    if (e.get("type") or "").lower() == "power":
        out.add("scaling")
    elif "scaling" in out and "this turn" in text and not re.search(r"Poison|Doom|Forge", text):
        out.discard("scaling")      # temporary buffs (e.g. Setup Strike) aren't scaling
    return out


def _version(v: str | None) -> tuple[int, ...] | None:
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums) if nums else None


def root_dir() -> Path | None:
    """knowledge/ as shipped in the package, or at the repo root when running from a checkout."""
    here = Path(__file__).resolve().parent
    for p in (here / "annotations", here.parents[1] / "knowledge"):
        if (p / "SCHEMA.md").exists():
            return p
    return None


class GameTexts:
    """Card text fingerprints per game version, from the game-data files the builder keeps for each version."""

    def __init__(self) -> None:
        self._cache: dict[Path, tuple[float, dict[str, str]]] = {}

    def _dir(self) -> Path:
        return data_home() / "knowledge" / "game"

    def _file_for(self, build: str | None) -> Path | None:
        want = _version(build)
        if not want:
            return None
        for f in self._dir().glob("game-*.json"):
            if _version(f.stem.removeprefix("game-")) == want:
                return f
        return None

    def hashes(self, build: str | None) -> dict[str, str] | None:
        f = self._file_for(build)
        if not f:
            return None
        try:
            mtime = f.stat().st_mtime
            if f in self._cache and self._cache[f][0] == mtime:
                return self._cache[f][1]
            from .gamedata import text_hash
            items = json.loads(f.read_text(encoding="utf-8"))
            h = {norm(e["id"]): e.get("text_hash") or text_hash(e.get("text") or "")
                 for e in items if isinstance(e, dict) and e.get("kind") == "card" and e.get("id")}
        except (OSError, ValueError):
            return None
        self._cache[f] = (mtime, h)
        return h


class Annotations:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else root_dir()
        self.cards: dict[str, dict] = {}            # norm(id) -> annotation (+ "_file")
        self.chars: dict[str, dict] = {}            # "ironclad" -> archetypes.yaml
        self.problems: list[str] = []
        self.texts = GameTexts()
        self._stamp: tuple = ()
        self.reload()

    # ------------------------------------------------------------ loading
    def _files(self) -> list[Path]:
        if not self.root or not self.root.exists():
            return []
        return sorted(p for d in self.root.iterdir() if d.is_dir() for p in d.glob("*.yaml"))

    def reload(self) -> None:
        cards, chars, problems = {}, {}, []
        files = self._files()
        for f in files:
            try:
                doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as e:
                problems.append(f"{f.parent.name}/{f.name}: {e}")
                continue
            if not isinstance(doc, dict):
                continue
            if f.name == "cards.yaml":
                for c in doc.get("cards") or []:
                    if isinstance(c, dict) and c.get("id"):
                        cards[norm(c["id"])] = {**c, "_file": f"{f.parent.name}/cards.yaml"}
            elif f.name == "archetypes.yaml":
                chars[f.parent.name] = doc
        self.cards, self.chars, self.problems = cards, chars, problems
        self._stamp = tuple((str(f), f.stat().st_mtime) for f in files)

    def refresh(self) -> None:
        """Reload if a file was added, removed or edited (cheap; called before each run summary)."""
        files = self._files()
        try:
            stamp = tuple((str(f), f.stat().st_mtime) for f in files)
        except OSError:
            stamp = ()
        if stamp != self._stamp:
            self.reload()

    # ------------------------------------------------------------ per card
    def get(self, card_id: str) -> dict | None:
        return self.cards.get(norm(card_id))

    def archetype_doc(self, character: str) -> dict | None:
        return self.chars.get((character or "").lower())

    def roles(self, card_id: str, kb: Knowledge) -> tuple[set[str], bool]:
        """(roles, annotated). Unannotated cards fall back to the text heuristic."""
        a = self.get(card_id)
        if a:
            return set(a.get("roles") or []), True
        return text_roles(card_id, kb), False

    def mechanics(self, card_id: str, kb: Knowledge) -> tuple[dict[str, str], bool]:
        """({mechanic tag: enabler | payoff | both}, annotated). Unannotated cards fall back to the mechanics tags
        the game-data builder read from the card's text (mechanics.py), where the tag names match."""
        a = self.get(card_id)
        if a:
            return {m["tag"]: m["as"] for m in a.get("mechanics") or [] if m.get("tag")}, True
        e = kb.get("card", card_id) or {}
        en, rw = set(e.get("enables") or []), set(e.get("rewards") or [])
        return {t: "both" if t in en and t in rw else "enabler" if t in en else "payoff" for t in en | rw}, False

    def review_state(self, card_id: str, run_build: str | None) -> dict:
        """status (draft/reviewed), by, build, and staleness: 'ok', 'stale' (text changed since review.build),
        or 'unchecked' (no review build, or no game data for one of the two versions to compare)."""
        a = self.get(card_id) or {}
        rv = a.get("review") or {}
        out = {"status": rv.get("status", "draft"), "by": rv.get("by", "?"), "build": rv.get("build", "unverified")}
        reviewed_v, run_v = _version(out["build"]), _version(run_build)
        if not reviewed_v:
            out["fresh"] = "unchecked"
        elif run_v and run_v <= reviewed_v:
            out["fresh"] = "ok"
        else:
            then, now = self.texts.hashes(out["build"]), self.texts.hashes(run_build)
            if then is None or now is None or norm(card_id) not in then or norm(card_id) not in now:
                out["fresh"] = "unchecked"
            else:
                out["fresh"] = "stale" if then[norm(card_id)] != now[norm(card_id)] else "ok"
        return out

    # ------------------------------------------------------------ per deck
    def snapshot(self, cards: list[dict], character: str, kb: Knowledge, prefer: str | None = None) -> dict:
        """Role counts and archetype states for one deck (SCHEMA.md §3). `prefer`: the previous primary archetype,
        kept on a tie so the primary doesn't flip back and forth between equal archetypes."""
        ids = [c["id"] for c in cards]
        roles = Counter({r: 0 for r in ROLES})
        role_cards: dict[str, list[str]] = {r: [] for r in ROLES}
        unannotated: list[str] = []
        for i in ids:
            if is_basic(i) or kb.card_type(i) in ("Curse", "Status"):
                continue
            rs, annotated = self.roles(i, kb)
            if not annotated:
                unannotated.append(i)
            for r in rs:
                if r in roles:
                    roles[r] += 1
                    role_cards[r].append(i)
        snap = {"size": len(ids), "roles": dict(roles), "role_cards": role_cards, "unannotated": unannotated,
                "archetypes": {}, "primary": None}
        doc = self.archetype_doc(character)
        if not doc:
            return snap
        weight = int(doc.get("keystone_weight") or 2)
        mechs = {i: self.mechanics(i, kb) for i in set(ids)}
        for a in doc.get("archetypes") or []:
            m = a.get("mechanic")
            keystones = {norm(k) for k in a.get("keystones") or []}
            E = P = E_text = P_text = 0
            for i in ids:
                tags, annotated = mechs[i]
                role = tags.get(m)
                if role in ("enabler", "both"):
                    E += 1
                    E_text += not annotated
                if role in ("payoff", "both"):
                    P += 1 + ((weight - 1) if norm(i) in keystones else 0)
                    P_text += not annotated
            thr = (a.get("thresholds") or {}).get("committed") or {}
            ce, cp = int(thr.get("enablers", 0)), int(thr.get("payoffs", 1))
            if E == 0 and P == 0:
                state = "absent"
            elif E >= ce and P >= cp:
                state = "committed"
            elif P >= cp:
                state = "half_built"
            else:
                state = "forming"
            short = {r: (roles.get(r, 0), n) for r, n in (a.get("support") or {}).items() if roles.get(r, 0) < n}
            snap["archetypes"][a["id"]] = {"name": a.get("name", a["id"]), "mechanic": m, "E": E, "P": P,
                                           "E_text": E_text, "P_text": P_text, "need": (ce, cp), "state": state,
                                           "support_ok": not short, "support_short": short}
        committed = [(v["E"] + v["P"], k) for k, v in snap["archetypes"].items() if v["state"] == "committed"]
        if committed:
            best = max(n for n, _ in committed)
            top = [k for n, k in committed if n == best]
            snap["primary"] = prefer if prefer in top else top[0]           # ties: the previous one, else file order
        return snap

    def orphans(self, snap: dict, cards: list[dict], kb: Knowledge) -> list[tuple[str, list[str]]]:
        """Annotated cards whose only value is a mechanic nothing else in the deck uses, and whose roles add nothing
        the deck would otherwise lack. -> [(card id, its mechanics)]
        A mechanic is in use when its archetype is committed, or when any other card in the deck feeds or pays it
        off (a half-built archetype is reported on its own). Only payoffs, or enablers with no roles at all, can be
        orphans: an enabler that also blocks or draws (Shrug It Off feeding Barricade) is there for its roles."""
        committed = {v["mechanic"] for v in snap["archetypes"].values() if v["state"] == "committed"}
        copies = Counter(c["id"] for c in cards)
        touches = {i: set(self.mechanics(i, kb)[0]) for i in copies}
        out = []
        for i, n in copies.items():
            a = self.get(i)
            if not a or is_basic(i):
                continue
            mechs = {m["tag"]: m.get("as") for m in a.get("mechanics") or [] if m.get("tag")}
            if not mechs:
                continue
            others = set().union(*(t for j, t in touches.items() if j != i))
            if any(t in committed or t in others for t in mechs):
                continue
            if a.get("roles") and not any(v in ("payoff", "both") for v in mechs.values()):
                continue
            if any(snap["roles"].get(r, 0) - n <= 0 for r in a.get("roles") or []):
                continue                    # the deck would lack this role without the card
            out.append((i, list(mechs)))
        return out
