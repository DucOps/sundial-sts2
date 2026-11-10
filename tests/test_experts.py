"""Expert cards: the frontmatter reader, the slots, and the file access guards."""
from __future__ import annotations

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from sundial_sts2 import experts as X

CARD = """---
name: Steady Hand
description: Slow and deliberate
kind: persona
characters: [IRONCLAD, silent]
version: 1.0
---
# Steady Hand

Block first, then scale.
"""


class TestFrontmatter:
    def test_reads_keys_lists_and_the_body(self):
        meta, body = X.parse_frontmatter(CARD)
        assert meta["name"] == "Steady Hand"
        assert meta["characters"] == ["IRONCLAD", "silent"]
        assert body.startswith("# Steady Hand")

    def test_a_card_without_frontmatter_is_all_body(self):
        meta, body = X.parse_frontmatter("# Just a card\n")
        assert meta == {} and body == "# Just a card\n"

    def test_comments_and_lines_without_a_colon_are_skipped(self):
        meta, _ = X.parse_frontmatter("---\n# a comment\nname: X\nbroken line\n---\nbody")
        assert meta == {"name": "X"}

    def test_quotes_are_stripped(self):
        meta, _ = X.parse_frontmatter("---\nname: 'Quoted Name'\nkind: \"persona\"\n---\n")
        assert meta == {"name": "Quoted Name", "kind": "persona"}


class TestCards:
    def test_create_writes_the_template(self, experts_dir):
        path = X.create("steady-hand", "Steady Hand", "calm")
        assert (path / "expert.md").exists() and (path / "sources").is_dir()
        assert "Steady Hand" in (path / "expert.md").read_text(encoding="utf-8")

    @pytest.mark.parametrize("slug", ["Steady Hand", "x", "way-too-" + "long" * 20, "under_score"])
    def test_create_refuses_a_bad_slug(self, experts_dir, slug):
        with pytest.raises(ToolError, match="Slug must be"):
            X.create(slug, "Name")

    def test_create_refuses_a_second_card_with_the_same_slug(self, experts_dir):
        X.create("steady-hand", "Steady Hand")
        with pytest.raises(ToolError, match="already exists"):
            X.create("steady-hand", "Other")

    def test_list_reports_meta_and_word_count(self, experts_dir):
        X.create("steady-hand", "Steady Hand", "calm")
        X.save_card("steady-hand", CARD)
        found = {e["slug"]: e for e in X.all_experts()}["steady-hand"]
        assert found["name"] == "Steady Hand" and found["kind"] == "persona"
        assert found["card_words"] == 7 and found["enabled"] is False     # "# Steady Hand" counts too

    def test_folders_without_a_card_are_not_experts(self, experts_dir):
        (experts_dir / "empty").mkdir()
        assert X.all_experts() == []

    def test_get_card_of_an_unknown_slug(self, experts_dir):
        with pytest.raises(ToolError, match="No expert 'nope'"):
            X.get_card("nope")

    def test_save_card_needs_name_and_description(self, experts_dir):
        X.create("steady-hand", "Steady Hand")
        with pytest.raises(ToolError, match="missing: name, description"):
            X.save_card("steady-hand", "---\nkind: persona\n---\nbody")

    def test_save_card_keeps_the_previous_card_as_a_backup(self, experts_dir):
        X.create("steady-hand", "Steady Hand", "calm")
        X.save_card("steady-hand", CARD)
        card = experts_dir / "steady-hand" / "expert.md"
        first = card.read_text(encoding="utf-8")
        X.save_card("steady-hand", CARD.replace("Block first", "Draw first"))
        assert (card.parent / "expert.md.bak").read_text(encoding="utf-8") == first

    def test_a_card_over_the_size_cap_is_refused(self, experts_dir):
        X.create("steady-hand", "Steady Hand")
        with pytest.raises(ToolError, match="keep it under"):
            X.save_card("steady-hand", CARD + "x" * (X.MAX_CARD_CHARS + 1))


class TestSlots:
    def test_enabling_keeps_the_order_it_was_enabled_in(self, experts_dir):
        for slug in ("one", "two", "three"):
            X.create(slug, slug.title())
        X.set_enabled("three", True)
        X.set_enabled("one", True)
        # the folder listing is alphabetical; the slots keep the order they were enabled in
        assert [meta["slug"] for meta, _ in X.enabled_cards()] == ["three", "one"]

    def test_disabling_removes_the_slot(self, experts_dir):
        X.create("one", "One")
        X.set_enabled("one", True)
        assert X.set_enabled("one", False) == []

    def test_enabled_cards_marks_experts_that_do_not_cover_the_character(self, experts_dir):
        X.create("one", "One")
        X.save_card("one", CARD.replace("IRONCLAD, silent", "SILENT"))
        X.set_enabled("one", True)
        [(meta, _text)] = X.enabled_cards("IRONCLAD")
        assert meta["covers_character"] is False
        [(meta, _text)] = X.enabled_cards("SILENT")
        assert meta["covers_character"] is True

    def test_an_expert_listed_in_the_config_but_deleted_is_skipped(self, experts_dir):
        X.create("one", "One")
        X.set_enabled("one", True)
        import shutil
        shutil.rmtree(experts_dir / "one")
        assert X.enabled_cards() == []


class TestSources:
    def test_lists_markdown_and_text_with_word_counts(self, experts_dir):
        d = X.create("steady-hand", "Steady Hand") / "sources"
        (d / "notes.md").write_text("one two three", encoding="utf-8")
        (d / "ignore.docx").write_bytes(b"x")
        assert X.list_sources("steady-hand") == [{"file": "notes.md", "words": 3}]

    def test_reads_in_chunks(self, experts_dir):
        d = X.create("steady-hand", "Steady Hand") / "sources"
        (d / "notes.md").write_text("abcdefghij", encoding="utf-8")
        assert X.read_source("steady-hand", "notes.md", 0, 4) == "abcd\n\n[… 6 more characters; call again with offset=4]"
        assert X.read_source("steady-hand", "notes.md", 8) == "ij"

    @pytest.mark.parametrize("name", ["../expert.md", "../../config.json", "/etc/hostname", "sub/../expert.md"])
    def test_a_source_path_never_escapes_the_sources_folder(self, experts_dir, name):
        X.create("steady-hand", "Steady Hand")
        with pytest.raises(ToolError, match="No source"):
            X.read_source("steady-hand", name)
