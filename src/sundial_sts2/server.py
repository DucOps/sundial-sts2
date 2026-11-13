"""Sundial MCP server: your Slay the Spire 2 run history as tools for Claude.

Run with:  sundial-sts2        (stdio transport, for Claude Desktop / Claude Code)
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError

from . import __version__
from . import analysis as A
from . import experts as X
from .gamedata import Updater, read_state
from .annotations import Annotations
from .knowledge import Knowledge
from .parse import MODE_NAME, pretty
from .store import Store, data_home

INSTRUCTIONS = """Tools for the player's own Slay the Spire 2 run history (read from their save files and
archived permanently). Use get_run_summary for post-game analysis of a run; it already contains the
floor-by-floor log, comparisons with the player's own history, and what each card/relic does.
Follow the sundial-sts2-analyst skill when writing an analysis. Never invent card or relic effects:
use lookup when unsure, and say so when data is missing.
Experts are optional coaching cards the player has enabled: after the Sundial analyst's own report, call get_enabled_experts
and write one separate section per expert, using only that expert's card."""

mcp = MCPServer("sundial-sts2", instructions=INSTRUCTIONS, version=__version__)
store = Store()
kb = Knowledge()
ann = Annotations()                     # card annotations and archetypes (knowledge/)
updater = Updater(data_home())          # builds game knowledge from the install; rebuilds after a game patch
updater.on_done = kb.reload


def _runs():
    updater.ensure()
    store.sync()
    return store.runs()


def _mode(mode: str | None) -> str | None:
    try:
        return A.check_mode(mode)
    except ValueError as e:
        raise ToolError(str(e)) from None


def _positive(name: str, n: int | None) -> None:
    if n is not None and n < 1:
        raise ToolError(f"{name} must be 1 or more (got {n}).")


def _unreadable_note() -> str:
    """A line naming archive files that couldn't be read, so a run missing from a list is explained."""
    bad = store.unreadable()
    if not bad:
        return ""
    names = ", ".join(b["file"] for b in bad[:5]) + (f" and {len(bad) - 5} more" if len(bad) > 5 else "")
    return f"\nNote: {len(bad)} archived file(s) couldn't be read and are not listed: {names}. status shows why."


MODE_FIELD = "game mode: standard, daily, blitz or dread; custom for custom games"
CHARS = "e.g. IRONCLAD, SILENT, DEFECT, NECROBINDER, REGENT, FOOL"


def _get(run: str):
    runs = _runs()
    r = A.resolve(runs, run)
    if not r:
        raise ToolError(f"No run matches '{run}'. Use list_runs to see run ids.")
    return runs, r


@mcp.tool(description="List recent runs, newest first. Returns run id, date, character, ascension (with the game mode "
                      "when it isn't Standard, e.g. 'Blitz A3'), result, floor, killer, version.")
def list_runs(
    character: Annotated[str | None, Field(description=CHARS)] = None,
    ascension: int | None = None,
    outcome: Annotated[str | None, Field(description="win, death or abandoned")] = None,
    version: Annotated[str | None, Field(description="game build, e.g. v0.111.0")] = None,
    mode: Annotated[str | None, Field(description=MODE_FIELD + "; omit for every mode")] = None,
    limit: Annotated[int, Field(description="how many runs to show, 1 or more")] = 20,
) -> str:
    _positive("limit", limit)
    m = _mode(mode)
    runs = [r for r in _runs()
            if (not character or r.character == character.upper())
            and (ascension is None or r.ascension == ascension)
            and (not outcome or r.outcome == outcome.lower())
            and (not version or r.build == version)
            and A.mode_ok(r, m)]
    rows = [A.run_row(r) for r in reversed(runs[-limit:])]
    return (f"{len(runs)} runs match; showing {len(rows)}.\nid | date | character | result | floor | killed by | version\n"
            + "\n".join(rows) + _unreadable_note())


@mcp.tool(description="The full analysis-ready summary of one run: outcome, comparisons with the player's own "
                      "baselines, deck roles and archetype states at each boss (with commit floors, pivots and how far "
                      "the card annotations can be trusted), final deck/relics, floor-by-floor log, and what each "
                      "card/relic does. "
                      "Start every post-game analysis here.")
def get_run_summary(
    run: Annotated[str, Field(description="'latest', 'latest_death', 'latest_win', 'previous', '-2' (2nd newest), or a run id from list_runs")] = "latest",
    glossary: Annotated[str, Field(description="'deck' (default: deck, relics, potions), 'full' (also every card offered), or 'none'")] = "deck",
) -> str:
    runs, r = _get(run)
    return A.digest(runs, r, kb, glossary, ann) + _unreadable_note()


@mcp.tool(description="The deck at every card reward, shop and boss of a run: role counts (front-load, AoE, scaling, "
                      "block, draw, energy, ...) and each archetype's state (absent / forming / committed / half_built, "
                      "with enabler and payoff counts). Use to see when a plan formed, stalled or changed.")
def get_deck_snapshots(
    run: Annotated[str, Field(description="'latest', 'latest_death', 'latest_win', 'previous', '-2' (2nd newest), or a run id from list_runs")] = "latest",
) -> str:
    runs, r = _get(run)
    ann.refresh()
    return A.snapshots_table(r, A.archetype_report(r, kb, ann), ann)


@mcp.tool(description="Everything recorded for one floor of a run, as raw fields (use when the summary isn't detailed enough).")
def get_floor(run: str, floor: int) -> str:
    _, r = _get(run)
    f = next((x for x in r.floors if x.f == floor), None)
    if not f:
        raise ToolError(f"Run {r.id} has floors 1–{r.floors_reached}.")
    d = {k: v for k, v in f.__dict__.items() if v not in (None, "", [], 0)}
    d["hp_before"] = f.hp_before
    d["encounter"] = f.encounter
    return json.dumps(d, indent=1)


@mcp.tool(description="The player's history against one encounter (boss, elite or hallway fight): times fought, damage taken, turns, deaths.")
def encounter_history(
    encounter: Annotated[str, Field(description="encounter id or name, e.g. PHROG_PARASITE_ELITE, 'Phrog Parasite' or part of a name")],
    character: str | None = None,
    ascension: int | None = None,
    mode: Annotated[str | None, Field(description=MODE_FIELD + ", or all")] = "standard",
) -> str:
    runs = _runs()
    m = _mode(mode)
    ids, close = A.match_ids(encounter, {f.encounter for r in runs for f in r.floors if f.encounter}, "ENCOUNTER.")
    if not ids:
        sug = f" Did you mean: {', '.join(pretty(i) for i in close)}?" if close else ""
        return f"No fights found matching '{encounter}'.{sug}"
    return json.dumps([A.encounter_stats(runs, i, character.upper() if character else None, ascension, mode=m)
                       for i in ids], indent=1)


@mcp.tool(description="One card across your runs: card rewards where it was offered and what you did, shop buys and "
                      "other gains, whether it was still in the final deck, and how runs that took it ended. Use it for "
                      "questions like 'should I take Offering?'.")
def card_history(
    card: Annotated[str, Field(description="card id or name, e.g. OFFERING, 'Pommel Strike' or part of a name")],
    character: Annotated[str | None, Field(description=CHARS + "; omit for all")] = None,
    ascension: int | None = None,
    last_n: Annotated[int | None, Field(description="only the newest N runs, 1 or more")] = None,
    mode: Annotated[str | None, Field(description=MODE_FIELD + ", or all")] = "standard",
) -> str:
    _positive("last_n", last_n)
    return A.card_history(_runs(), card, character, ascension, last_n, _mode(mode))


@mcp.tool(description="Patterns across many runs: win rate, act clear rates, deaths by room, top killers, card pick habits, "
                      "rest-site habits, potions held at death. Use for coaching beyond a single run.")
def player_summary(
    character: Annotated[str | None, Field(description=CHARS + "; omit for all")] = "IRONCLAD",
    ascension: int | None = None,
    last_n: Annotated[int | None, Field(description="only the newest N runs, 1 or more")] = None,
    mode: Annotated[str | None, Field(description=MODE_FIELD + ", or all")] = "standard",
) -> str:
    _positive("last_n", last_n)
    return A.player_summary(_runs(), character, ascension, last_n, kb, ann, _mode(mode))


@mcp.tool(description="Ascension progress for a character in one game mode: tries per level, first clear date, "
                      "version it was won on. Blitz has its own A1–A5 ladder, so modes are never mixed.")
def ascension_climb(
    character: Annotated[str, Field(description=CHARS)] = "IRONCLAD",
    mode: Annotated[str, Field(description=MODE_FIELD)] = "standard",
) -> str:
    m = _mode(mode)
    if m in (None, "all"):
        raise ToolError("ascension_climb needs one mode: standard, daily, blitz, dread or custom.")
    return A.climb(_runs(), character, m)


@mcp.tool(description="Runs and wins per game version (early access build).")
def version_summary() -> str:
    return A.versions(_runs())


LOOKUP_KINDS = ["card", "relic", "potion", "power", "keyword", "enchantment", "orb", "character", "monster",
                "encounter", "act", "event", "ascension", "term"]


@mcp.tool(description="Look up game facts from the player's install: what cards, relics, potions, powers, keywords, "
                      "enchantments and orbs do; characters' starting kits; monsters' HP and moves; encounters; acts; events "
                      "and Ancients; "
                      "ascension levels; glossary terms. Data can be from an older game version; say so if it matters.")
def lookup(
    names: Annotated[list[str], Field(description="ids or names, e.g. ['BLOODLETTING', 'Burning Blood']")],
    kind: Annotated[str | None, Field(description="card, relic, potion, power, keyword, enchantment, orb, character, "
                                                  "monster, encounter, act, event, ascension or term; omit to search all")] = None,
) -> str:
    updater.ensure()
    out = []
    for n in names:
        kinds = [kind] if kind else LOOKUP_KINDS
        hit = next(((k, kb.get(k, n)) for k in kinds if kb.get(k, n)), None)
        if hit:
            out.append(f"{hit[0]}: {kb.describe(hit[0], n)}")
        else:
            near = kb.search(n.replace("_", " "), kind, 3)
            out.append(f"{n}: no data" + (f" (did you mean {', '.join(e['name'] for e in near)}?)" if near else ""))
    return "\n".join(out)


@mcp.tool(description="Search the official patch notes that ship with the player's game, e.g. to see when a card, relic "
                      "or enemy changed. Returns matching lines with their patch date, newest first. With no query, "
                      "lists the patches.")
def patch_notes(
    query: Annotated[str | None, Field(description="a card, relic, enemy or keyword name or id, e.g. 'Inflame'")] = None,
    since: Annotated[str | None, Field(description="only patches on or after this date (YYYY-MM-DD)")] = None,
    limit: Annotated[int, Field(description="how many lines or patches to show, 1 or more")] = 25,
) -> str:
    _positive("limit", limit)
    if since:
        since = since.strip()
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
                raise ValueError
            date.fromisoformat(since)
        except ValueError:
            raise ToolError(f"since must be a date as YYYY-MM-DD, e.g. 2026-08-01 (got '{since}').") from None
    updater.ensure()
    f = data_home() / "knowledge" / "game" / "patch-notes.json"
    try:
        notes = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "No patch notes yet: they're read from the game install when game knowledge is built (see status)."
    notes = [n for n in notes if isinstance(n, dict) and isinstance(n.get("text"), str)]
    for n in notes:
        n["date"] = n["date"] if isinstance(n.get("date"), str) and n["date"] else "undated"
    notes = [n for n in notes if not since or (n["date"] != "undated" and n["date"] >= since)][::-1]
    if not query:
        return "\n".join(f"{n['date']}: {next((l.strip('# ') for l in n['text'].splitlines() if l.strip()), '')[:120]}"
                         for n in notes[:limit])
    terms = {query.lower()}
    for k in LOOKUP_KINDS:
        e = kb.get(k, query)
        if e and e.get("name"):
            terms.add(e["name"].lower())
    hits = []
    for n in notes:
        for line in n["text"].splitlines():
            if any(t in line.lower() for t in terms):
                hits.append(f"{n['date']}: {line.strip()}")
    if not hits:
        return f"No patch-note lines mention {' / '.join(sorted(terms))}" + (f" since {since}" if since else "") + "."
    more = f"\n({len(hits) - limit} more; narrow with since)" if len(hits) > limit else ""
    return "\n".join(hits[:limit]) + more


# ---------------------------------------------------------------- lessons (personal coaching notes)
def _lessons_path():
    p = data_home() / "lessons.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_lessons() -> list[dict]:
    try:
        return json.loads(_lessons_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


@mcp.tool(description="The player's saved lessons from earlier analyses. Read before analysing so you can say whether "
                      "a known habit showed up again.")
def get_lessons(character: str | None = None) -> str:
    raw = _load_lessons()
    raw = raw if isinstance(raw, list) else []
    good = [l for l in raw if isinstance(l, dict) and isinstance(l.get("text"), str) and l["text"].strip()]
    ls = [l for l in good if not character or l.get("character") in (None, "", character.upper())]
    skipped = len(raw) - len(good)
    note = f"\n({skipped} entr{'y' if skipped == 1 else 'ies'} in lessons.json had no text and were skipped.)" if skipped else ""
    if not ls:
        return "No saved lessons yet." + note
    def who(l: dict) -> str:        # with no character filter, say whose lesson it is
        c = l.get("character")
        return f" · {pretty(c)}" if not character and isinstance(c, str) and c else ""
    return "\n".join(f"- [{l.get('date') or 'undated'}] {l['text'].strip()}" + (f" (run {l['run']})" if l.get("run") else "")
                     + who(l) for l in ls) + note


@mcp.tool(description="Save a lesson the player agreed with, so future analyses can track it. Only call when the player asks to save it.")
def save_lesson(text: str, run: str | None = None, character: str | None = None) -> str:
    ls = _load_lessons()
    ls.append({"date": datetime.now().strftime("%Y-%m-%d"), "text": text.strip(), "run": run,
               "character": character.upper() if character else None})
    _lessons_path().write_text(json.dumps(ls, indent=1, ensure_ascii=False), encoding="utf-8")
    return f"Saved. {len(ls)} lessons on file."


# ---------------------------------------------------------------- experts (expansion slots)
@mcp.tool(description="List installed expert cards (optional coaching perspectives) and which are enabled.")
def list_experts() -> str:
    ex = X.all_experts()
    if not ex:
        return (f"No experts installed. Experts live in {X.experts_dir()}. "
                "Use create_expert to start one, or copy an expert folder there.")
    return json.dumps(ex, indent=1)


_MODE_NOTE = {
    "notes": "(NOTE: {mode} run. Apply this card's {mode} notes (under Mode notes) wherever they differ from its general "
             "principles.)",
    "not_covered": "(NOTE: this card's modes don't include {mode}. Write one line saying it doesn't cover {mode} runs and "
                   "skip.)",
    "not_applicable": "(NOTE: {mode} run, and this {kind} card has no {mode} notes: the advice it summarises wasn't written "
                      "for {mode}. Write one line, '*Not applicable in {mode}: this card's sources don't cover it.*', and "
                      "skip.)",
    "guardrails": "(NOTE: {mode} run, and this card has no {mode} notes. Apply it, but skip principles about routing, "
                  "elite counts, gold and shops, which {mode} doesn't offer, and say in one line which you skipped.)",
}


@mcp.tool(description="Cards of the experts the player has enabled, in slot order. Call after writing the Sundial analyst report, "
                      "then write one section per expert using only that card. Pass the run's character and game mode so "
                      "experts that don't cover them are marked.")
def get_enabled_experts(
    character: str | None = None,
    mode: Annotated[str | None, Field(description=MODE_FIELD + "; the run's mode")] = None,
) -> str:
    m = _mode(mode)
    cards = X.enabled_cards(character, None if m == "all" else m)
    if not cards:
        return "No experts enabled. Skip the expert sections."
    parts = []
    name = MODE_NAME.get(m or "", (m or "").title())
    for i, (meta, text) in enumerate(cards, 1):
        if not meta["covers_character"]:
            note = f"\n(NOTE: this expert's card doesn't cover {character}; say so in one line and skip.)"
        elif meta["mode_status"] in _MODE_NOTE:
            note = "\n" + _MODE_NOTE[meta["mode_status"]].format(mode=name, kind=meta.get("kind") or "")
        else:
            note = ""
        parts.append(f"===== SLOT {i}: {meta['name']} ({meta['slug']}) ====={note}\n{text.strip()}")
    return "\n\n".join(parts)


@mcp.tool(description="Enable or disable an expert for analyses. Enabled experts appear in the order they were enabled.")
def set_expert_enabled(slug: str, enabled: bool = True) -> str:
    order = X.set_enabled(slug, enabled)
    return f"{'Enabled' if enabled else 'Disabled'} {slug}. Slots now: {', '.join(order) or 'none'}."


@mcp.tool(description="Show one expert's full card.")
def get_expert(slug: str) -> str:
    return X.get_card(slug)


@mcp.tool(description="Create a new expert (a viewpoint the player writes) with a template card and an empty sources/ folder for their notes.")
def create_expert(
    slug: Annotated[str, Field(description="lowercase-with-hyphens id, e.g. 'steady-hand'")],
    name: str,
    description: str = "",
) -> str:
    d = X.create(slug, name, description)
    return (f"Created {d} with a template card. Fill it in by hand, use the write_expert prompt to be interviewed, "
            f"or put your own notes (.md/.txt) in {d / 'sources'} and use the build_expert prompt.")


@mcp.tool(description="List an expert's source files (the player's notes) with word counts.")
def list_expert_sources(slug: str) -> str:
    src = X.list_sources(slug)
    return json.dumps(src, indent=1) if src else "No source files. Add .md or .txt files to the expert's sources/ folder."


@mcp.tool(description="Read one source file of an expert, in chunks. Use offset to continue a long file.")
def read_expert_source(slug: str, file: str, offset: int = 0) -> str:
    return X.read_source(slug, file, offset)


@mcp.tool(description="Save (create or replace) an expert's card. Must start with frontmatter including name and description. "
                      "The previous card is kept as expert.md.bak. Only call when the player has approved the card.")
def save_expert_card(slug: str, markdown: str) -> str:
    return f"Saved {X.save_card(slug, markdown)}."


@mcp.prompt(description="Write a new expert with Claude: it interviews you about the viewpoint, drafts the card and saves it once you approve.")
def write_expert(idea: str = "") -> str:
    seed = f" My starting idea: {idea}." if idea else ""
    return ("Help me write a Sundial expert card using the sundial-sts2-analyst skill's 'Writing an expert with the "
            "player' steps. Interview me one question at a time, then draft the card in the template's shape." + seed)


@mcp.prompt(description="Build or update an expert card from your own notes in its sources/ folder.")
def build_expert(slug: str) -> str:
    return (f"Build the expert card for '{slug}' from my notes using the sundial-sts2-analyst skill's 'Building an expert "
            f"card from notes' steps. Start with get_expert('{slug}') and list_expert_sources('{slug}').")


# ---------------------------------------------------------------- saved analyses (shown in the dashboard)
def _analyses_dir():
    d = data_home() / "analyses"
    d.mkdir(parents=True, exist_ok=True)
    return d


@mcp.tool(description="Save a finished analysis so the dashboard can show it, with each expert as a separate, "
                      "toggleable section. Call once per analysis after writing it. `experts` is a list of "
                      "{slug, name, kind, verdict, markdown}; `core_markdown` is the Sundial analyst report without expert slots.")
def save_analysis(
    run: str,
    verdict: Annotated[str, Field(description="the Sundial analyst report's one-sentence verdict")],
    core_markdown: str,
    experts: Annotated[list[dict], Field(description="one entry per expert slot: slug, name, kind, verdict (one line), markdown")] = [],
    experts_differ: Annotated[str, Field(description="the 'Where the experts differ' line, if any")] = "",
) -> str:
    _, r = _get(run)
    known = {e["slug"]: e for e in X.all_experts()}
    clean = []
    for e in experts:
        slug = str(e.get("slug", "")).strip()
        if not slug or not e.get("markdown"):
            raise ToolError("Each expert needs a slug and markdown.")
        meta = known.get(slug, {})
        clean.append({"slug": slug, "name": e.get("name") or meta.get("name", slug), "kind": e.get("kind") or meta.get("kind", ""),
                      "card_version": meta.get("version", ""), "verdict": e.get("verdict", ""), "markdown": e["markdown"]})
    doc = {"type": "sundial-sts2-analysis", "version": 1, "run_key": r.key, "run_id": r.id,
           "character": r.character, "ascension": r.ascension, "outcome": r.outcome,
           "created": datetime.now().isoformat(timespec="seconds"),
           "core": {"verdict": verdict, "markdown": core_markdown}, "experts": clean, "experts_differ": experts_differ}
    p = _analyses_dir() / f"{r.id}.json"
    if p.exists():
        (_analyses_dir() / f"{r.id}.{datetime.now():%Y%m%d%H%M%S}.bak.json").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    return f"Saved to {p}. Import ~/.sundial-sts2/analyses (or the whole ~/.sundial-sts2 folder) in the dashboard to view it."


@mcp.tool(description="Where runs are read from and archived, how many are loaded, and what game data is available.")
def status() -> str:
    updater.ensure()
    s = store.sync()
    runs = store.runs()
    bad = store.unreadable()
    st = read_state(data_home())
    game_knowledge = {"status": updater.status, "built_for": st.get("game_version"), "built": st.get("built"),
                      "entries": st.get("entries")}
    if updater.error:
        game_knowledge["error"] = updater.error + " (still using the last good knowledge)"
    return json.dumps({**s, "runs_loaded": len(runs), "runs_unreadable": len(bad),
                       **({"unreadable": bad} if bad else {}),
                       "latest_run": A.run_row(runs[-1]) if runs else None,
                       "game_knowledge": game_knowledge,
                       "knowledge_entries": len(kb.entries), "knowledge_files": kb.loaded_from,
                       "card_annotations": {"dir": str(ann.root) if ann.root else None, "cards": len(ann.cards),
                                            "characters_with_archetypes": sorted(ann.chars),
                                            **({"problems": ann.problems} if ann.problems else {})},
                       "experts_dir": str(X.experts_dir()),
                       "experts": [f"{e['slug']}{' (enabled)' if e['enabled'] else ''}" for e in X.all_experts()]}, indent=1)


@mcp.prompt(description="Post-game analysis of a run: what went wrong, what could have gone better.")
def analyse_run(run: str = "latest") -> str:
    return (f"Analyse my Slay the Spire 2 run '{run}' using the sundial-sts2-analyst skill. "
            f"Start with get_run_summary(run='{run}') and get_lessons, then add a section for each enabled expert.")


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
