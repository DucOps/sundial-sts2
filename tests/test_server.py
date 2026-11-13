"""Tool inputs are checked, unreadable files are reported, and runs are only compared within one game mode."""
import importlib
import json
import shutil

import pytest
from conftest import FIXTURES
from mcp.server.mcpserver.exceptions import ToolError


@pytest.fixture
def srv(home):
    _, saves = home
    for f in FIXTURES.glob("*.run"):
        shutil.copy2(f, saves / f.name)
    from sundial_sts2 import server
    s = importlib.reload(server)
    return lambda name, **kw: getattr(getattr(s, name), "fn", getattr(s, name))(**kw)


def _add(home, name, d):
    (home[1] / name).write_text(json.dumps(d), encoding="utf-8")


def test_status_reports_unreadable_files(srv, home):
    _add(home, "1790400000.run", {"hello": 1})
    st = json.loads(srv("status"))
    assert st["runs_loaded"] == 3 and st["runs_unreadable"] == 1
    assert st["unreadable"][0]["file"] == "profile1/1790400000.run"
    assert "1790400000.run" in srv("list_runs")


def test_status_without_problems_has_no_list(srv):
    st = json.loads(srv("status"))
    assert st["runs_unreadable"] == 0 and "unreadable" not in st


@pytest.mark.parametrize("tool,kw", [("list_runs", {"limit": 0}), ("list_runs", {"limit": -1}),
                                     ("player_summary", {"last_n": 0}), ("player_summary", {"last_n": -2}),
                                     ("patch_notes", {"limit": 0}),
                                     ("patch_notes", {"since": "2026"}), ("patch_notes", {"since": "2026-8-1"}),
                                     ("patch_notes", {"since": "2026-02-30"}),
                                     ("list_runs", {"mode": "endless"}), ("ascension_climb", {"mode": "all"}),
                                     ("card_history", {"card": "Headbutt", "last_n": 0}),
                                     ("card_history", {"card": "Headbutt", "last_n": -1})])
def test_bad_inputs_are_refused(srv, tool, kw):
    with pytest.raises(ToolError):
        srv(tool, **kw)


def test_empty_since_means_no_filter(srv):
    srv("patch_notes", since="")


def test_list_runs_limit(srv):
    assert "showing 1." in srv("list_runs", limit=1)


def test_lessons_survive_hand_edits(srv, home):
    (home[0]).mkdir(parents=True, exist_ok=True)
    (home[0] / "lessons.json").write_text(json.dumps(
        [{"text": "no date"}, {"date": "2026-01-01"}, "junk", {"date": "2026-01-02", "text": "ok", "character": "IRONCLAD"}]),
        encoding="utf-8")
    out = srv("get_lessons")
    assert "[undated] no date" in out and "[2026-01-02] ok · Ironclad" in out and "2 entries" in out
    assert "· Ironclad" not in srv("get_lessons", character="IRONCLAD")


def test_first_run_of_a_mode_has_no_baseline(srv, home, raw):
    d = raw()
    d["start_time"], d["game_mode"] = 1790300000, "blitz"
    _add(home, "1790300000.run", d)
    out = srv("get_run_summary", run="latest")
    assert out.startswith("# Run 1790300000: Ironclad Blitz A10")
    assert "first finished Blitz Ironclad run" in out and "no baseline" in out
    assert "base values" in out or "Enemies in the deciding fights" not in out


def test_modes_are_kept_apart(srv, home, raw):
    d = raw()
    d["start_time"], d["game_mode"] = 1790300000, "blitz"
    _add(home, "1790300000.run", d)
    assert "No Blitz runs" not in srv("ascension_climb", character="IRONCLAD", mode="blitz")
    assert srv("player_summary", character="IRONCLAD").startswith("# 3 runs")
    assert srv("player_summary", character="IRONCLAD", mode="all").startswith("# 4 runs")
    assert "Blitz A10" in srv("list_runs") and "4 runs match" in srv("list_runs")
    assert "1 runs match" in srv("list_runs", mode="blitz")


def test_encounter_names(srv):
    assert '"encounter": "PHROG_PARASITE_ELITE"' in srv("encounter_history", encounter="Parasite")
    assert "Did you mean: Phrog Parasite?" in srv("encounter_history", encounter="Pharog Parasite")


def test_card_history_tool(srv):
    assert srv("card_history", card="Headbutt").startswith("# Headbutt")
    assert "No runs match." == srv("card_history", card="Headbutt", mode="blitz")
