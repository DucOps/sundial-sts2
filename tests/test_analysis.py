"""Cross-run tables on the fixtures: the climb, baselines, encounter history, the run summary's sections,
card_history and name matching. Dates are built with fmt_date, so the tests pass in any timezone."""
import json

import pytest
from conftest import FIXTURES

from sundial_sts2 import analysis as A
from sundial_sts2.knowledge import Knowledge
from sundial_sts2.parse import parse_run


@pytest.fixture
def runs():
    return [parse_run(json.loads(f.read_text(encoding="utf-8"))) for f in sorted(FIXTURES.glob("*.run"))]


def _raw_offers(card):
    """Offers and picks of one card at card rewards (not shop stock), counted straight from the fixture JSON."""
    offers = picks = 0
    runs = set()
    for f in FIXTURES.glob("*.run"):
        d = json.loads(f.read_text(encoding="utf-8"))
        for pt in [p for act in d["map_point_history"] for p in act]:
            if pt["map_point_type"] == "shop":
                continue
            for c in pt["player_stats"][0].get("card_choices") or []:
                if c["card"]["id"] == f"CARD.{card}":
                    offers, picks = offers + 1, picks + bool(c["was_picked"])
                    runs.add(f.name)
    return offers, picks, len(runs)


def test_climb_counts_tries_deaths_and_the_first_win(runs):
    out = A.climb(runs, "IRONCLAD")
    first, win = runs[0], runs[-1]
    assert f"| A10 | 3 | 1 | 1 | {A.fmt_date(first.start)[4:15]} | {A.fmt_date(win.start)[4:15]} | {win.build} |" in out


def test_peers_widen_to_nearby_ascensions(runs):
    peers, desc = A.peers(runs, runs[-1])
    assert [p.outcome for p in peers] == ["death"] and desc == "your 1 finished Ironclad runs at A9–A11"


def test_encounter_stats_count_the_death(runs):
    death = next(r for r in runs if r.outcome == "death")
    st = A.encounter_stats(runs, death.killer)
    assert st["deaths"] == 1 and st["fought"] >= 1 and st["kind"] in ("boss", "elite", "monster")


def test_run_summary_sections(runs):
    death = next(r for r in runs if r.outcome == "death")
    out = A.digest(runs, death, Knowledge())
    for part in ("## How it ended", "## This run vs your baseline", "## Deck at each boss (reconstructed)", "## Floor log"):
        assert part in out


@pytest.mark.parametrize("card,query", [("HEADBUTT", "Headbutt"), ("PERFECTED_STRIKE", "perfected strike")])
def test_card_history_counts_picks_not_runs(runs, card, query):
    offers, picks, n = _raw_offers(card)
    out = A.card_history(runs, query)
    assert f"offered {offers}× in {n} runs; taken {picks}×" in out


def test_card_history_names(runs):
    assert A.card_history(runs, "Headbut").startswith("# Headbutt")
    assert "Did you mean: Headbutt?" in A.card_history(runs, "Hedbutt")
    assert "only in the starting deck" in A.card_history(runs, "Bash")
    assert A.card_history(runs, "Headbutt", last_n=1).startswith("# Headbutt: 1 of 1 runs")


def test_match_ids():
    ids = {"PHROG_PARASITE_ELITE", "VANTOM_BOSS", "SLIMES_WEAK"}
    assert A.match_ids("Parasite", ids) == (["PHROG_PARASITE_ELITE"], [])
    assert A.match_ids("PHROG", ids) == (["PHROG_PARASITE_ELITE"], [])
    assert A.match_ids("ENCOUNTER.VANTOM_BOSS", ids, "ENCOUNTER.") == (["VANTOM_BOSS"], [])
    assert A.match_ids("Vantum", ids) == ([], ["VANTOM_BOSS"])
    assert A.match_ids("", ids) == ([], [])


def test_profile_facts_cover_every_mode_and_link_runs():
    from conftest import MODES
    every = sorted((parse_run(json.loads(f.read_text(encoding="utf-8"))) for d in (FIXTURES, MODES) for f in d.glob("*.run")),
                   key=lambda r: r.start)
    out = A.player_profile_facts(every, verdicts=[{"run_id": 1, "character": "Ironclad", "level": "A10", "outcome": "win",
                                                  "verdict": "VERDICT-LINE"}], lessons=[{"text": "LESSON-LINE"}])
    win = next(r for r in every if r.outcome == "win" and r.bucket == "standard")
    assert f"A10 won on try 3 ({A.fmt_date(win.start)[4:15]}, run {win.id};" in out          # same tries as climb()
    assert "| Blitz |" in out and "| Fool |" in out                                          # never filtered to one mode
    assert "first ever Blitz run" in out and "first ever Fool run" in out
    assert "VERDICT-LINE" in out and "LESSON-LINE" in out
    for header in ("## Modes and characters", "## Climbs", "## Drafting and deck", "## Records", "## When they play"):
        assert header in out


def test_profile_facts_merge_cards_by_name():
    from collections import Counter
    assert A._top(Counter({"STRIKE_IRONCLAD": 3, "STRIKE_SILENT": 2, "BASH": 4}), 2) == "Strike 5, Bash 4"


def test_profile_facts_without_runs():
    assert A.player_profile_facts([]) == "No runs yet."
