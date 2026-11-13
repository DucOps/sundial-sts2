"""Expert cards: optional, user-supplied coaching perspectives that plug into run analysis.

An expert is a viewpoint the player writes themselves (a persona, their own rules, or their summary of a guide).
It is a folder in the experts directory (default ~/.sundial-sts2/experts):

    experts/
      steady-hand/
        expert.md        the card: frontmatter + principles (this is what the analyst reads)
        sources/         optional: the player's own notes the card was written from

Only `expert.md` is sent to the analyst, so keep it focused (aim for under ~1,500 words).
Which experts are enabled is stored in ~/.sundial-sts2/config.json.

Game modes: Standard, Daily and Dread play on the usual map, so every card applies. Blitz (fixed 8-room acts, gold
that doesn't change, a merchant selling services) breaks advice about routing, elites and gold, so for a Blitz run
each card gets a status (see mode_status): its own Blitz notes, the general card with guardrails, or not applicable.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from .store import data_home

TEMPLATE = (Path(__file__).parent / "expert_template.md")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}$")
MAX_CARD_CHARS = 20000
# kinds that summarise someone else's advice: without notes for a mode, the card can't speak for it
SOURCED_KINDS = ("creator", "community")
# modes whose rules differ enough from Standard that cards need their own notes
NOTED_MODES = ("blitz",)


def experts_dir() -> Path:
    return Path(os.environ.get("SUNDIAL_EXPERTS", data_home() / "experts"))


def _config_path() -> Path:
    return data_home() / "config.json"


def _config() -> dict:
    try:
        return json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_config(cfg: dict) -> None:
    _config_path().parent.mkdir(parents=True, exist_ok=True)
    _config_path().write_text(json.dumps(cfg, indent=1), encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Tiny frontmatter reader: `key: value` and `key: [a, b]` lines between --- markers."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    meta: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            meta[k.strip()] = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
        else:
            meta[k.strip()] = v.strip("'\"")
    return meta, m.group(2)


def mode_notes(body: str, mode: str) -> str:
    """The card's notes for one mode: the '### Blitz' subsection under '## Mode notes', or ''."""
    sec = re.search(r"^##\s+Mode notes\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S | re.I)
    if not sec:
        return ""
    sub = re.search(rf"^###\s+{re.escape(mode)}\s*$(.*?)(?=^###?\s|\Z)", sec.group(1), re.M | re.S | re.I)
    text = sub.group(1).strip() if sub else ""
    return "" if re.fullmatch(r"(<!--.*?-->\s*)*", text, re.S) else text


def mode_status(meta: dict, body: str, mode: str | None) -> str:
    """How a card applies to a run of `mode`:
    'ok'             a mode played on the usual map (or none given): the card applies as written
    'notes'          the card has notes for this mode: apply them over the general principles
    'not_covered'    the card's `modes` leave this mode out
    'not_applicable' a creator or community card with no notes for this mode: its sources don't cover it
    'guardrails'     any other card: apply it, but skip principles about routing, elite counts, gold and shops"""
    mode = (mode or "").lower()
    modes = [m.lower() for m in (meta.get("modes") or ["all"])]
    if mode and "all" not in modes and mode not in modes:
        return "not_covered"
    if mode not in NOTED_MODES:
        return "ok"
    if mode_notes(body, mode):
        return "notes"
    if meta.get("kind", "") in SOURCED_KINDS and mode not in modes:
        return "not_applicable"
    return "guardrails"


def _dir(slug: str) -> Path:
    """An expert's folder. The slug comes from the AI, so it must be a plain name: never a path outside the folder."""
    if not isinstance(slug, str) or not SLUG.match(slug):
        raise ToolError(f"'{slug}' isn't an expert name: use lowercase letters, digits and hyphens, e.g. 'steady-hand'.")
    return experts_dir() / slug


def _card_path(slug: str) -> Path:
    return _dir(slug) / "expert.md"


def all_experts() -> list[dict]:
    enabled = set(_config().get("enabled_experts", []))
    out = []
    root = experts_dir()
    if not root.exists():
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        card = d / "expert.md"
        if not card.exists():
            continue
        meta, body = parse_frontmatter(card.read_text(encoding="utf-8"))
        sources = d / "sources"
        out.append({
            "slug": d.name, "name": meta.get("name", d.name), "description": meta.get("description", ""),
            "kind": meta.get("kind", ""), "characters": meta.get("characters", ["all"]),
            "modes": meta.get("modes", ["all"]),
            "blitz_notes": bool(mode_notes(body, "blitz")),
            "version": meta.get("version", ""), "enabled": d.name in enabled,
            "card_words": len(body.split()),
            "source_files": len(list(sources.glob("*"))) if sources.exists() else 0,
        })
    return out


def get_card(slug: str) -> str:
    p = _card_path(slug)
    if not p.exists():
        raise ToolError(f"No expert '{slug}'. Use list_experts.")
    return p.read_text(encoding="utf-8")


def enabled_cards(character: str | None = None, mode: str | None = None) -> list[tuple[dict, str]]:
    """Cards of enabled experts, in the order they were enabled, each marked with whether it covers `character`
    and how it applies to a run of `mode` (mode_status)."""
    order = _config().get("enabled_experts", [])
    known = {e["slug"]: e for e in all_experts()}
    out = []
    for slug in order:
        e = known.get(slug)
        if not e:
            continue
        chars = [c.upper() for c in e["characters"]]
        covers = not character or "ALL" in chars or character.upper() in chars
        text = get_card(slug)
        meta, body = parse_frontmatter(text)
        out.append(({**e, "covers_character": covers, "mode_status": mode_status(meta, body, mode)}, text))
    return out


def set_enabled(slug: str, enabled: bool) -> list[str]:
    if not _card_path(slug).exists():
        raise ToolError(f"No expert '{slug}'. Use list_experts.")
    cfg = _config()
    order = [s for s in cfg.get("enabled_experts", []) if s != slug]
    if enabled:
        order.append(slug)
    cfg["enabled_experts"] = order
    _save_config(cfg)
    return order


def create(slug: str, name: str, description: str = "") -> Path:
    if not SLUG.match(slug):
        raise ToolError("Slug must be lowercase letters, digits and hyphens, e.g. 'steady-hand'.")
    d = experts_dir() / slug
    if (d / "expert.md").exists():
        raise ToolError(f"Expert '{slug}' already exists.")
    (d / "sources").mkdir(parents=True, exist_ok=True)
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("{{name}}", name).replace("{{slug}}", slug).replace("{{description}}", description or "One line: who this is and what lens they bring.")
    (d / "expert.md").write_text(text, encoding="utf-8")
    return d


def save_card(slug: str, markdown: str) -> str:
    meta, body = parse_frontmatter(markdown)
    missing = [k for k in ("name", "description") if not meta.get(k)]
    if missing:
        raise ToolError(f"Card frontmatter is missing: {', '.join(missing)}.")
    if len(markdown) > MAX_CARD_CHARS:
        raise ToolError(f"Card is {len(markdown)} characters; keep it under {MAX_CARD_CHARS}. Move raw material to sources/.")
    p = _card_path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        (p.parent / "expert.md.bak").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text(markdown, encoding="utf-8")
    return str(p)


def list_sources(slug: str) -> list[dict]:
    d = _dir(slug) / "sources"
    if not d.exists():
        return []
    return [{"file": f.name, "words": len(f.read_text(encoding="utf-8", errors="ignore").split())}
            for f in sorted(d.iterdir()) if f.is_file() and f.suffix.lower() in (".md", ".txt")]


def read_source(slug: str, file: str, offset: int = 0, limit: int = 40000) -> str:
    d = (_dir(slug) / "sources").resolve()
    p = (d / file).resolve()
    if d not in p.parents or not p.exists():
        raise ToolError(f"No source '{file}' for '{slug}'.")
    text = p.read_text(encoding="utf-8", errors="ignore")
    chunk = text[offset:offset + limit]
    more = f"\n\n[… {len(text) - offset - limit} more characters; call again with offset={offset + limit}]" if offset + limit < len(text) else ""
    return chunk + more
