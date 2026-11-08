"""Game knowledge lookup: what cards, relics, potions, powers and keywords do.

Knowledge files are JSON lists of entries:
  {"id": "SHRUG_IT_OFF", "kind": "card", "name": "Shrug It Off", "text": "...",
   "character": "Ironclad", "type": "Skill", "cost": "1", "rarity": "Common",
   "enables": ["..."], "rewards": ["..."], "refs": ["Block"], "source": "...", "as_of": "v0.111.0"}
Kinds: card, relic, potion, power (Vulnerable, Plating, ...), keyword (Exhaust, Retain, ...).

Files are read from, in order (later entries override earlier ones):
  1. <package>/knowledge/*.json                   (shipped, licence-clean data only)
  2. ~/.sundial-sts2/knowledge/game/<current>     (built from your game install; see gamedata.py)
  3. ~/.sundial-sts2/knowledge/*.json              (your local data: imports, your own notes)

Nothing here is required. Unknown ids are reported as unknown so the analyst
never invents what a card does.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .parse import pretty
from .store import data_home


def norm(s: str) -> str:
    s = re.sub(r"^(STRIKE|DEFEND)_(IRONCLAD|SILENT|DEFECT|NECROBINDER|REGENT)$", r"\1", s.upper())
    return re.sub(r"[^A-Z0-9]", "", s)


class Knowledge:
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str], dict] = {}
        self.by_name: dict[tuple[str, str], dict] = {}
        self.loaded_from: list[str] = []
        self.reload()

    def reload(self) -> None:
        entries: dict[tuple[str, str], dict] = {}
        by_name: dict[tuple[str, str], dict] = {}
        loaded: list[str] = []
        files = sorted((Path(__file__).parent / "knowledge").glob("*.json"))
        game_dir = data_home() / "knowledge" / "game"
        try:
            current = json.loads((game_dir / "current.json").read_text(encoding="utf-8")).get("file")
            if current and (game_dir / current).exists():
                files.append(game_dir / current)
        except (OSError, ValueError):
            pass
        files += sorted((data_home() / "knowledge").glob("*.json"))
        for f in files:
            try:
                items = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for e in items if isinstance(items, list) else []:
                if e.get("id") and e.get("kind"):
                    entries[(e["kind"], norm(e["id"]))] = e
                    if e.get("name"):
                        by_name[(e["kind"], norm(e["name"]))] = e
            loaded.append(str(f))
        # swap in one go: the server may reload from a background thread while a tool is reading
        self.entries, self.by_name, self.loaded_from = entries, by_name, loaded

    def get(self, kind: str, id_: str) -> dict | None:
        return self.entries.get((kind, norm(id_))) or self.by_name.get((kind, norm(id_)))

    def card_type(self, id_: str) -> str:
        e = self.get("card", id_)
        if e and e.get("type"):
            return e["type"]
        if id_ in ("ASCENDERS_BANE", "CLUMSY", "INJURY", "DECAY", "DOUBT", "REGRET", "SHAME", "WRITHE", "PARASITE"):
            return "Curse"
        return "Unknown"

    def describe(self, kind: str, id_: str) -> str:
        e = self.get(kind, id_)
        name = pretty(id_)
        if not e:
            return f"{name}: (no data; don't guess its effect)"
        bits = [b for b in (e.get("type"), (f"{e['cost']} energy" if e.get("cost") not in (None, "") else ""),
                            e.get("rarity")) if b]
        meta = f" [{', '.join(bits)}]" if bits else ""
        return f"{e.get('name') or name}{meta}: {e.get('text', '').strip()}"

    def search(self, query: str, kind: str | None = None, limit: int = 10) -> list[dict]:
        q = query.lower()
        hits = [e for (k, _), e in list(self.entries.items())
                if (kind is None or k == kind) and (q in (e.get("name") or "").lower() or q in (e.get("text") or "").lower())]
        return hits[:limit]
