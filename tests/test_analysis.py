"""The analysis layer: run lookup, baselines, tables, the digest, and one card across runs."""
from __future__ import annotations

import pytest

from conftest import ABANDONED, DEATH, WIN
from sundial_sts2 import analysis as A


class TestResolve:
    def test_latest_is_the_most_recent_run(self, runs):
        assert A.resolve(runs, "latest").id == 1790200000
        assert A.resolve(runs, None).id == 1790200000

    def test_latest_death_and_latest_win(self, runs):
        assert A.resolve(runs, "latest_death").id == 1790100000
        assert A.resolve(runs, "latest_win").id == 1790200000

    def test_previous_is_the_one_before_the_newest(self, runs):
        assert A.resolve(runs, "previous").id == 1790100000

    def test_negative_index_counts_back_from_the_newest(self, runs):
        assert A.resolve(runs, "-1").id == 1790200000
        assert A.resolve(runs, "-3").id == 1790000000
        assert A.resolve(runs, "-4") is None

    def test_a_run_id_and_a_seed(self, runs):
        assert A.resolve(runs, "1790100000").id == 1790100000
        assert A.resolve(runs, str(runs[0].seed).lower()).id == 1790000000

    def test_an_unknown_ref_and_an_empty_archive(self, runs):
        assert A.resolve(runs, "no-such-run") is None
        assert A.resolve([], "latest") is None


class TestPeers:
    def test_widens_to_one_ascension_either_side(self, runs):
        win = runs[-1]
        peers, desc = A.peers([runs[1], win], win)
        assert [p.id for p in peers] == [1790100000]
        assert "A9–A11" in desc

    def test_a_first_finished_run_says_so_instead_of_counting_zero(self, runs):
        win = runs[-1]
        peers, desc = A.peers([win], win)
        assert peers == []
        assert desc == "no other finished Ironclad run yet"
        assert "0 finished" not in desc

    def test_abandoned_runs_are_not_baselines(self, runs):
        peers, _ = A.peers(runs, runs[-1])
        assert all(p.outcome != "abandoned" for p in peers)


class TestEncounterStats:
    def test_counts_fights_damage_and_deaths(self, runs):
        stats = A.encounter_stats(runs, "VANTOM_BOSS")
        assert stats["name"] == "Vantom" and stats["kind"] == "boss"
        assert stats["fought"] == 2                     # the death run and the win both reached it
        assert stats["avg_damage"] is not None and stats["worst_damage"] >= stats["avg_damage"]
        assert stats["deaths"] == 0

    def test_the_excluded_run_does_not_count_towards_its_own_baseline(self, runs):
        win = runs[-1]
        assert A.encounter_stats(runs, "VANTOM_BOSS")["fought"] == 2
        assert A.encounter_stats(runs, "VANTOM_BOSS", exclude_key=win.key)["fought"] == 1

    def test_an_encounter_you_never_fought(self, runs):
        stats = A.encounter_stats(runs, "NOT_A_FIGHT")
        assert stats["fought"] == 0 and stats["avg_damage"] is None and stats["death_rate"] is None

    def test_filters_on_character_and_ascension(self, runs):
        assert A.encounter_stats(runs, "VANTOM_BOSS", character="IRONCLAD")["fought"] == 2
        assert A.encounter_stats(runs, "VANTOM_BOSS", character="SILENT")["fought"] == 0
        assert A.encounter_stats(runs, "VANTOM_BOSS", ascension=0)["fought"] == 0


class TestDeckReconstruction:
    def test_the_deck_after_the_last_floor_is_the_final_deck(self, runs):
        for r in runs:
            rebuilt = sorted(c["id"] for c in A.deck_at(r, r.floors_reached + 1) if c["id"])
            assert rebuilt == sorted(c["id"] for c in r.deck if c["id"])

    def test_a_card_removed_later_is_still_in_the_deck_at_an_earlier_boss(self, runs):
        win = runs[-1]
        removed = [f for f in win.floors if f.removed]
        assert removed, "the fixture win removes a card, so this test would otherwise prove nothing"
        first_boss = A._boss_floor(win, 1)
        before = [c["id"] for c in A.deck_at(win, first_boss.f)]
        assert removed[0].removed[0] in before

    def test_profile_counts_basics_and_upgrades(self, runs, kb):
        win = runs[-1]
        profile = A.deck_profile(A.deck_at(win, win.floors_reached + 1), kb)
        assert profile["size"] == len(win.deck)
        assert profile["basics"] == 6                   # 4 Defends + 2 Strikes left at the end of the fixture win
        assert sum(profile["types"].values()) == profile["size"]


class TestTables:
    def test_versions_are_newest_first_and_count_wins(self, runs):
        table = A.versions(runs)
        lines = table.splitlines()
        assert lines[0].startswith("| Version | Runs | Wins")
        assert "| v0.111.0 | 3 | 1 |" in table

    def test_climb_counts_tries_deaths_and_the_first_win(self, runs):
        table = A.climb(runs, "IRONCLAD")
        assert "| A10 | 3 | 1 | 1 | 21 Sep 2026 | 23 Sep 2026 | v0.111.0 |" in table
        # an ascension that has not been won says so instead of leaving the cell empty
        assert "not yet" in A.climb(runs[:1], "IRONCLAD")

    def test_climb_for_an_unplayed_character(self, runs):
        assert A.climb(runs, "DEFECT") == "No runs for that character."

    def test_run_row_lines_up_with_the_header(self, runs):
        row = A.run_row(runs[-1]).split(" | ")
        assert len(row) == 7 and row[2] == "Ironclad A10" and row[3] == "win"


class TestPlayerSummary:
    def test_reports_win_rate_and_habits(self, runs, kb, ann):
        text = A.player_summary(runs, None, None, None, kb, ann)
        assert "3 runs (all characters)" in text
        assert "Wins 1 of 2 finished (50%), 1 abandoned" in text
        assert "Median floor 33" in text
        assert "Act 1 boss reached 2 (100%), cleared 2 (100%)" in text
        assert "Deaths by room: Boss 1" in text
        assert "Rest sites: rested 5×" in text

    def test_filters_and_last_n(self, runs, kb, ann):
        text = A.player_summary(runs, "IRONCLAD", 10, 1, kb, ann)
        assert "1 runs (Ironclad, A10)" in text

    def test_no_matching_runs(self, runs, kb):
        assert A.player_summary(runs, "DEFECT", None, None, kb) == "No runs match."


class TestDigest:
    def test_a_win_lists_three_bosses_and_a_floor_log(self, runs, kb, ann):
        text = A.digest(runs, runs[-1], kb, "deck", ann)
        assert text.startswith("# Run 1790200000: Ironclad A10, Victory on floor 49")
        assert "## Floor log" in text and "F49 A3 B" in text
        assert "## Deck at each boss (reconstructed)" in text
        assert "| Act 1 boss (F17)" not in text          # the table is per-boss rows, not a duplicate header
        assert "Knowledge confidence" in text

    def test_a_death_names_the_killer_and_its_history(self, runs, kb, ann):
        death = runs[1]
        text = A.digest(runs, death, kb, "none", ann)
        assert "Died on floor 33" in text and "Knowledge Demon" in text
        assert "## How it ended" in text
        assert "Final room: floor 33, Act 2 Boss" in text
        assert "Gold at death" in text

    def test_the_glossary_modes_differ(self, runs, kb, ann):
        deck = A.digest(runs, runs[-1], kb, "deck", ann)
        none = A.digest(runs, runs[-1], kb, "none", ann)
        assert "What things do" in deck and "What things do" not in none

    def test_one_run_says_there_is_no_baseline_yet(self, runs, kb, ann):
        win = runs[-1]
        text = A.digest([win], win, kb, "none", ann)
        assert "No baseline yet: no other finished Ironclad run yet" in text
        assert "your 0 finished" not in text

    def test_an_abandoned_five_floor_run_still_renders(self, runs, kb, ann):
        early = runs[0]
        text = A.digest(runs, early, kb, "deck", ann)
        assert "Abandoned on floor 5" in text
        assert "## Floor log" in text and "F5  A1 H" in text

    def test_a_run_with_no_floors_does_not_raise(self, runs, kb, ann):
        empty = runs[0].__class__(**{**vars(runs[0]), "floors": []})
        text = A.digest([empty], empty, kb, "none", ann)
        assert "# Run" in text and "## Floor log" in text


class TestCardHistory:
    def test_counts_offers_picks_and_kept_cards(self, runs):
        text = A.card_history(runs, "Offering")
        assert text.startswith("# Offering: offered ")
        assert "runs that passed on it" in text
        assert "Counts, not proof" in text

    def test_accepts_an_id_or_a_name(self, runs):
        by_name = A.card_history(runs, "Demon Form")
        by_id = A.card_history(runs, "DEMON_FORM")
        assert by_name.splitlines()[0] == by_id.splitlines()[0]
        assert by_name.startswith("# Demon Form:")

    def test_shop_stock_is_not_an_offer(self, runs):
        # the fixtures sell cards in shops; those floors must not count as rewards (parse.py and parse.js agree)
        text = A.card_history(runs, "Offering")
        assert "Picked on" in text or "Never picked" in text
        assert "F22" not in text.split("Offers by act")[0]

    def test_a_card_you_were_never_offered_names_the_closest_ones(self, runs):
        text = A.card_history(runs, "Offring")
        assert "was never offered" in text
        assert "Offering" in text

    def test_respects_the_run_filters(self, runs):
        assert A.card_history(runs, "Offering", character="SILENT") == "No runs match."
        assert A.card_history(runs, "Offering", last_n=1).startswith("# Offering")

    def test_no_runs_match(self, runs):
        assert A.card_history([], "Offering") == "No runs match."
