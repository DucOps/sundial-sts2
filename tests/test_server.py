"""The MCP tools: what they answer, and the errors they raise instead of guessing."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from conftest import ABANDONED, DEATH, WIN, fixture_doc
from sundial_sts2 import server as S


def call(tool):
    """The plain function behind a registered MCP tool."""
    return getattr(tool, "fn", tool)


@pytest.fixture()
def home(monkeypatch, tmp_path) -> Path:
    d = tmp_path / "home"
    d.mkdir()
    monkeypatch.setenv("SUNDIAL_HOME", str(d))
    return d


class TestListRuns:
    def test_lists_every_run_newest_first(self, archive):
        out = call(S.list_runs)()
        assert out.startswith("3 runs match; showing 3.")
        assert out.splitlines()[2].startswith(str(WIN))
        assert out.splitlines()[-1].startswith(str(ABANDONED))

    def test_limit(self, archive):
        assert call(S.list_runs)(limit=1).startswith("3 runs match; showing 1.")

    @pytest.mark.parametrize("limit", [0, -1, -20])
    def test_a_limit_below_one_is_refused(self, archive, limit):
        # limit=0 used to return every run (runs[-0:] is the whole list), the opposite of what it asks for
        with pytest.raises(ToolError, match="limit must be at least 1"):
            call(S.list_runs)(limit=limit)

    def test_filters(self, archive):
        assert call(S.list_runs)(outcome="win").startswith("1 runs match")
        assert call(S.list_runs)(character="ironclad").startswith("3 runs match")
        assert call(S.list_runs)(character="SILENT").startswith("0 runs match")
        assert call(S.list_runs)(ascension=10).startswith("3 runs match")
        assert call(S.list_runs)(version="v0.111.0").startswith("3 runs match")
        assert call(S.list_runs)(version="v0.1.0").startswith("0 runs match")


class TestRunSummary:
    def test_the_default_is_the_latest_run(self, archive):
        out = call(S.get_run_summary)()
        assert out.startswith("# Run 1790200000: Ironclad A10, Victory")

    def test_a_missing_ref_names_the_alternatives(self, archive):
        with pytest.raises(ToolError, match="No run matches 'nope'. Use list_runs"):
            call(S.get_run_summary)(run="nope")


class TestFloor:
    def test_returns_the_floors_raw_fields(self, archive):
        data = json.loads(call(S.get_floor)(run="latest", floor=17))
        assert data["t"] == "B" and data["encounter"] == "VANTOM_BOSS" and data["dmg"] == 47

    def test_a_floor_the_run_never_reached_names_the_range(self, archive):
        with pytest.raises(ToolError, match=r"has floors 1–49"):
            call(S.get_floor)(run="latest", floor=50)


class TestEncounterHistory:
    def test_an_exact_id(self, archive):
        rows = json.loads(call(S.encounter_history)("VANTOM_BOSS"))
        assert [r["encounter"] for r in rows] == ["VANTOM_BOSS"]
        assert rows[0]["fought"] == 2

    def test_an_id_prefix_keeps_matching_every_variant(self, archive):
        rows = json.loads(call(S.encounter_history)("BYRDONIS"))
        assert {r["encounter"] for r in rows} >= {"BYRDONIS_ELITE"}

    def test_a_readable_name(self, archive):
        # the tool promises "an id or a name": a name used to answer "no fights found"
        rows = json.loads(call(S.encounter_history)("Vantom"))
        assert rows[0]["encounter"] == "VANTOM_BOSS" and rows[0]["name"] == "Vantom"

    def test_a_name_with_spaces(self, archive):
        assert json.loads(call(S.encounter_history)("Snapping Jaxfruit"))[0]["fought"] >= 1

    def test_an_unknown_fight_suggests_the_closest(self, archive):
        out = call(S.encounter_history)("Vantum")
        assert out.startswith("No fights found matching 'Vantum'.")
        assert "Vantom" in out

    def test_an_empty_query_is_refused(self, archive):
        with pytest.raises(ToolError, match="Give an encounter id or name"):
            call(S.encounter_history)("  ")

    def test_filters_reach_the_statistics(self, archive):
        assert json.loads(call(S.encounter_history)("VANTOM_BOSS", character="SILENT"))[0]["fought"] == 0


class TestStatus:
    def test_reports_sources_and_counts(self, archive):
        data = json.loads(call(S.status)())
        assert data["runs_loaded"] == 3 and data["runs_unreadable"] == 0
        assert data["scanned"] == 3
        assert "unreadable" not in data
        assert data["latest_run"].startswith(str(WIN))

    def test_names_a_file_it_could_not_read(self, archive):
        (archive / "profile1" / "1790555555.run").write_text("{", encoding="utf-8")
        data = json.loads(call(S.status)())
        assert data["runs_loaded"] == 3 and data["runs_unreadable"] == 1
        assert data["unreadable"][0]["file"] == "profile1/1790555555.run"
        assert "JSONDecodeError" in data["unreadable"][0]["error"]

    def test_a_missing_run_points_at_the_unreadable_files(self, archive):
        (archive / "profile1" / "1790555555.run").write_text("{", encoding="utf-8")
        with pytest.raises(ToolError, match="could not be read"):
            call(S.get_run_summary)(run="1790555555")

    def test_list_runs_mentions_unreadable_files(self, archive):
        (archive / "profile1" / "1790555555.run").write_text("{", encoding="utf-8")
        out = call(S.list_runs)()
        assert "could not be read" in out and "1790555555.run" in out


class TestLessons:
    def test_empty(self, archive, home):
        assert call(S.get_lessons)() == "No saved lessons yet."

    def test_save_then_read(self, archive, home):
        call(S.save_lesson)("Take Offering less", run="latest", character="ironclad")
        out = call(S.get_lessons)()
        assert "Take Offering less" in out and "(run latest)" in out
        assert call(S.get_lessons)(character="SILENT") == "No saved lessons yet."

    def test_a_hand_edited_entry_without_a_date_is_still_read(self, archive, home):
        # lessons.json is the player's own file; an entry that lost a field used to raise KeyError
        (home / "lessons.json").write_text(json.dumps([
            {"text": "no date here"},
            {"date": "2026-09-01", "text": "healthy entry"},
            {"date": "2026-09-02"},
            "not even an object",
        ]), encoding="utf-8")
        out = call(S.get_lessons)()
        assert "[undated] no date here" in out
        assert "[2026-09-01] healthy entry" in out
        assert "2 entries in lessons.json could not be read" in out

    def test_lessons_are_character_specific(self, archive, home):
        (home / "lessons.json").write_text(json.dumps([
            {"date": "2026-09-01", "text": "ironclad note", "character": "IRONCLAD"},
            {"date": "2026-09-02", "text": "silent note", "character": "SILENT"},
        ]), encoding="utf-8")
        assert call(S.get_lessons)(character="IRONCLAD") == "- [2026-09-01] ironclad note"

    def test_a_file_that_is_not_a_list_is_ignored(self, archive, home):
        (home / "lessons.json").write_text('{"note": "not a list"}', encoding="utf-8")
        assert call(S.get_lessons)() == "No saved lessons yet."


class TestCardHistoryTool:
    def test_by_name(self, archive):
        assert call(S.card_history)("Offering").startswith("# Offering: offered ")

    def test_an_empty_card_is_refused(self, archive):
        with pytest.raises(ToolError, match="Give a card id or name"):
            call(S.card_history)(" ")


class TestPatchNotes:
    def test_without_a_file(self, archive, home):
        assert "No patch notes yet" in call(S.patch_notes)()

    def test_a_hand_edited_note_without_a_date(self, archive, home):
        d = home / "knowledge" / "game"
        d.mkdir(parents=True)
        (d / "patch-notes.json").write_text(json.dumps([
            {"date": "2026-08-01", "text": "# Patch\n- Vantom now has 90 HP"},
            {"text": "# Undated\n- Offering costs 1"},
        ]), encoding="utf-8")
        out = call(S.patch_notes)()
        assert "2026-08-01: Patch" in out and "undated: Undated" in out

    def test_finds_a_line(self, archive, home):
        d = home / "knowledge" / "game"
        d.mkdir(parents=True)
        (d / "patch-notes.json").write_text(json.dumps([
            {"date": "2026-08-01", "text": "# Patch\n- Vantom now has 90 HP\n- Offering costs 1"}]), encoding="utf-8")
        assert call(S.patch_notes)("Vantom") == "2026-08-01: - Vantom now has 90 HP"

    @pytest.mark.parametrize("since", ["2026", "2026-08", "1 August", "2026-8-1"])
    def test_since_must_be_a_full_date(self, archive, home, since):
        # a bare year compares as a string and filters every patch out, silently
        with pytest.raises(ToolError, match="since must be a date like 2026-08-01"):
            call(S.patch_notes)(since=since)

    def test_since_filters(self, archive, home):
        d = home / "knowledge" / "game"
        d.mkdir(parents=True)
        (d / "patch-notes.json").write_text(json.dumps([
            {"date": "2026-07-01", "text": "# A\n- old line"},
            {"date": "2026-08-01", "text": "# B\n- new line"}]), encoding="utf-8")
        assert call(S.patch_notes)(since="2026-08-01").strip() == "2026-08-01: B"


class TestSaveAnalysis:
    def test_writes_the_run_and_cleans_the_expert_entries(self, archive, home, experts_dir):
        from sundial_sts2 import experts as X
        X.create("steady-hand", "Steady Hand", "calm")
        out = call(S.save_analysis)(run="latest", verdict="v", core_markdown="core",
                                    experts=[{"slug": "steady-hand", "markdown": "- ok"}])
        path = home / "analyses" / "1790200000.json"
        assert str(path) in out and path.exists()
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["run_key"].endswith(str(WIN)) and doc["character"] == "IRONCLAD"
        assert doc["experts"][0]["slug"] == "steady-hand"
        assert doc["experts"][0]["name"] == "Steady Hand"        # filled in from the card
        assert doc["core"] == {"verdict": "v", "markdown": "core"}

    def test_an_expert_needs_markdown(self, archive, home, experts_dir):
        with pytest.raises(ToolError, match="slug and markdown"):
            call(S.save_analysis)(run="latest", verdict="v", core_markdown="c", experts=[{"slug": "x"}])

    def test_saving_twice_keeps_a_backup(self, archive, home, experts_dir):
        call(S.save_analysis)(run="latest", verdict="v1", core_markdown="c")
        call(S.save_analysis)(run="latest", verdict="v2", core_markdown="c")
        assert list((home / "analyses").glob("1790200000.*.bak.json"))


class TestLookup:
    def test_an_unknown_card_says_so_instead_of_inventing_it(self, archive):
        assert call(S.lookup)(["NOT_A_CARD"]) == "NOT_A_CARD: no data"
