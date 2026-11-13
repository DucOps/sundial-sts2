"""Expert cards and game modes: in Blitz, a card applies with its own Blitz notes, with guardrails, or not at all."""
import importlib

import pytest

from sundial_sts2 import experts as X

CARD = """---
name: {name}
slug: {slug}
description: test
kind: {kind}
characters: [all]
{modes}version: 1
---

## Who this is
A test card.

## Core principles
1. **TT1 - Fight elites.** Three in Act 1.
{notes}
## Limits
None.
"""
BLITZ_NOTES = """
## Mode notes

### Blitz
TT1 doesn't apply: the elite is fixed. Take Card Removal at the merchant.
"""
EMPTY_NOTES = """
## Mode notes

### Blitz
<!-- nothing to say about Blitz -->
"""


def _card(home, slug, kind, notes="", modes=""):
    d = home / "experts" / slug
    d.mkdir(parents=True)
    (d / "expert.md").write_text(CARD.format(name=slug.title(), slug=slug, kind=kind, notes=notes, modes=modes),
                                 encoding="utf-8")
    X.set_enabled(slug, True)


@pytest.fixture
def experts(home):
    return home[0]


@pytest.mark.parametrize("kind,notes,modes,mode,status", [
    ("creator", "", "", "standard", "ok"),
    ("creator", "", "", "dread", "ok"),
    ("creator", "", "", None, "ok"),
    ("creator", "", "", "blitz", "not_applicable"),
    ("community", "", "", "blitz", "not_applicable"),
    ("community", EMPTY_NOTES, "", "blitz", "not_applicable"),
    ("community", BLITZ_NOTES, "", "blitz", "notes"),
    ("creator", "", "modes: [standard, blitz]\n", "blitz", "guardrails"),
    ("persona", "", "", "blitz", "guardrails"),
    ("personal", BLITZ_NOTES, "", "blitz", "notes"),
    ("persona", "", "modes: [standard, daily]\n", "blitz", "not_covered"),
    ("persona", "", "modes: [standard, daily]\n", "standard", "ok"),
])
def test_mode_status(experts, kind, notes, modes, mode, status):
    _card(experts, "tester", kind, notes, modes)
    (meta, _), = X.enabled_cards("IRONCLAD", mode)
    assert meta["mode_status"] == status


def test_mode_notes_are_only_the_blitz_subsection():
    meta, body = X.parse_frontmatter(CARD.format(name="A", slug="a", kind="persona", notes=BLITZ_NOTES, modes=""))
    assert X.mode_notes(body, "blitz") == "TT1 doesn't apply: the elite is fixed. Take Card Removal at the merchant."
    assert X.mode_notes(body, "dread") == ""


def test_get_enabled_experts_marks_each_slot(experts):
    _card(experts, "creator-card", "creator")
    _card(experts, "my-rules", "personal")
    _card(experts, "noted", "community", BLITZ_NOTES)
    from sundial_sts2 import server
    s = importlib.reload(server)
    out = getattr(s.get_enabled_experts, "fn", s.get_enabled_experts)(character="IRONCLAD", mode="blitz")
    slots = out.split("===== SLOT ")[1:]
    assert "Not applicable in Blitz" in slots[0]
    assert "skip principles about routing" in slots[1]
    assert "Apply this card's Blitz notes" in slots[2]
    std = getattr(s.get_enabled_experts, "fn", s.get_enabled_experts)(character="IRONCLAD")
    assert "NOTE" not in std


def test_the_template_has_no_blitz_notes():
    meta, body = X.parse_frontmatter(X.TEMPLATE.read_text(encoding="utf-8"))
    assert meta["modes"] == ["all"] and X.mode_notes(body, "blitz") == ""


def test_enabled_order_and_disable(experts):
    for slug in ("first-one", "second-one"):
        _card(experts, slug, "persona")
    assert [m["slug"] for m, _ in X.enabled_cards()] == ["first-one", "second-one"]
    X.set_enabled("first-one", False)
    X.set_enabled("first-one", True)
    assert [m["slug"] for m, _ in X.enabled_cards()] == ["second-one", "first-one"]
    X.set_enabled("second-one", False)
    assert [m["slug"] for m, _ in X.enabled_cards()] == ["first-one"]


def test_save_card_needs_frontmatter_and_keeps_a_backup(experts):
    from mcp.server.mcpserver.exceptions import ToolError
    _card(experts, "keeper", "persona")
    with pytest.raises(ToolError):
        X.save_card("keeper", "no frontmatter here")
    X.save_card("keeper", "---\nname: Keeper\ndescription: new\n---\nnew body")
    d = experts / "experts" / "keeper"
    assert "new body" in (d / "expert.md").read_text(encoding="utf-8")
    assert "A test card" in (d / "expert.md.bak").read_text(encoding="utf-8")


def test_read_source_in_chunks(experts):
    _card(experts, "noter", "personal")
    src = experts / "experts" / "noter" / "sources"
    src.mkdir()
    (src / "notes.md").write_text("abcdefghij", encoding="utf-8")
    assert X.list_sources("noter") == [{"file": "notes.md", "words": 1}]
    first = X.read_source("noter", "notes.md", limit=4)
    assert first.startswith("abcd") and "offset=4" in first
    assert X.read_source("noter", "notes.md", offset=8, limit=4) == "ij"


@pytest.mark.parametrize("call", [
    lambda: X.save_card("../../escaped", "---\nname: x\ndescription: y\n---\n"),
    lambda: X.get_card("../x"),
    lambda: X.set_enabled("..", True),
    lambda: X.list_sources("../../"),
    lambda: X.read_source("../x", "notes.md"),
    lambda: X.read_source("noter", "../expert.md"),
    lambda: X.read_source("noter", "../../../config.json"),
])
def test_names_and_paths_stay_inside_the_experts_folder(experts, call):
    from mcp.server.mcpserver.exceptions import ToolError
    _card(experts, "noter", "personal")
    (experts / "experts" / "noter" / "sources").mkdir()
    with pytest.raises(ToolError):
        call()
    assert not (experts / "escaped").exists() and not (experts.parent / "escaped").exists()
