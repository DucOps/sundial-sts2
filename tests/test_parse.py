"""The parser: ids, names, and the half-filled entries a damaged or older-schema save can hold."""
from __future__ import annotations

import pytest

from conftest import ABANDONED, DEATH, WIN, fixture_doc
from sundial_sts2.parse import (_dicts, _enchantment_of, _id_of, _num, _strings, encounter_kind, is_encounter,
                                looks_like_run, parse_run, pretty, strip_prefix, title_case)


class TestIds:
    @pytest.mark.parametrize("raw,expected", [
        ("CARD.STRIKE_IRONCLAD", "STRIKE_IRONCLAD"),
        ("MONSTER.VANTOM", "VANTOM"),
        ("BARE_ID", "BARE_ID"),
        ("", ""),
        (None, ""),
        (7, ""),
    ])
    def test_strip_prefix(self, raw, expected):
        assert strip_prefix(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("STRIKE_IRONCLAD", "Strike"),
        ("DEFEND_SILENT", "Defend"),
        ("ENCOUNTER.PHROG_PARASITE_ELITE", "Phrog Parasite"),
        ("BAG_OF_MARBLES", "Bag of Marbles"),
        ("", ""),
        ("NONE", ""),
    ])
    def test_pretty(self, raw, expected):
        assert pretty(raw) == expected

    def test_title_case_keeps_small_words_lower_after_the_first(self):
        assert title_case("THE_THORN_OF_WRATH") == "The Thorn of Wrath"
        assert title_case("OF") == "Of"

    @pytest.mark.parametrize("raw,expected", [
        ("VANTOM_BOSS", "boss"), ("BYRDONIS_ELITE", "elite"), ("CHOMPERS_NORMAL", "monster"),
        ("SNAPPING_JAXFRUIT_WEAK", "monster"), ("MYSTERY", ""),
    ])
    def test_encounter_kind(self, raw, expected):
        assert encounter_kind(raw) == expected

    def test_is_encounter(self):
        assert is_encounter("VANTOM_BOSS")
        assert not is_encounter("WELLSPRING")


class TestSaveFileGuards:
    """One odd entry must cost that entry, never the run: the archive is the only copy of a pruned run."""

    def test_dicts_ignores_anything_that_is_not_a_dict(self):
        assert _dicts([{"a": 1}, None, "x", 3]) == [{"a": 1}]
        assert _dicts(None) == []
        assert _dicts({"a": 1}) == []            # a dict where a list is expected is not a list of one

    def test_strings_ignores_non_strings(self):
        assert _strings(["A", None, 2, "B"]) == ["A", "B"]
        assert _strings("A") == []

    def test_id_of_walks_the_path_and_stops_safely(self):
        assert _id_of({"card": {"id": "CARD.BASH"}}, "card", "id") == "BASH"
        assert _id_of({"card": None}, "card", "id") == ""
        assert _id_of({"card": {"id": None}}, "card", "id") == ""
        assert _id_of("BASH", "card", "id") == ""
        assert _id_of({"id": 12}, "id") == ""

    def test_num_reads_whole_numbers_and_refuses_the_rest(self):
        assert _num(80) == 80
        assert _num(80.0) == 80
        assert _num(80.6) == 81
        assert _num("80") is None                # a string where a number belongs is not a number
        assert _num(None) is None
        assert _num(True) is None                # bool is an int subclass; it is not a HP value

    def test_enchantment_accepts_both_stored_shapes(self):
        assert _enchantment_of({"enchantment": "ENCHANTMENT.SHARP"}) == "SHARP"
        assert _enchantment_of({"enchantment": {"id": "ENCHANTMENT.SHARP"}}) == "SHARP"
        assert _enchantment_of({}) == ""


class TestLooksLikeRun:
    def test_accepts_a_fixture(self, doc):
        assert looks_like_run(doc)

    @pytest.mark.parametrize("missing", ["map_point_history", "players", "start_time"])
    def test_rejects_a_document_without_a_required_key(self, doc, missing):
        doc.pop(missing)
        assert not looks_like_run(doc)

    def test_rejects_a_non_dict(self):
        assert not looks_like_run([])
        assert not looks_like_run(None)


class TestParseFixtureRuns:
    def test_win(self):
        r = parse_run(fixture_doc(WIN), profile="profile1", file="win.run")
        assert (r.id, r.character, r.ascension, r.outcome) == (1790200000, "IRONCLAD", 10, "win")
        assert r.floors_reached == 49 and r.act_reached == 3
        assert [f.f for f in r.floors] == list(range(1, 50))
        assert r.key.startswith(r.seed)
        assert len(r.deck) == 27 and r.relics and r.potions_held == []

    def test_death(self):
        r = parse_run(fixture_doc(DEATH))
        assert (r.outcome, r.floors_reached) == ("death", 33)
        assert r.killer == "KNOWLEDGE_DEMON_BOSS" and r.killer_kind == "boss"

    def test_abandoned(self):
        r = parse_run(fixture_doc(ABANDONED))
        assert (r.outcome, r.floors_reached, r.killer) == ("abandoned", 5, "")

    def test_hp_before_undoes_the_damage_and_heal_of_the_floor(self):
        r = parse_run(fixture_doc(WIN))
        boss = r.floors[16]                       # F17, the Act 1 boss
        assert boss.t == "B" and boss.encounter == "VANTOM_BOSS"
        assert boss.dmg == 47 and boss.heal == 6
        assert boss.hp is not None
        assert boss.hp_before == boss.hp + 47 - 6

    def test_every_floor_has_a_glyph_the_reports_know(self):
        from sundial_sts2.parse import ROOM_NAME
        for name in (ABANDONED, DEATH, WIN):
            assert {f.t for f in parse_run(fixture_doc(name)).floors} <= set(ROOM_NAME)

    def test_deck_floors_are_kept_for_the_reconstruction(self):
        r = parse_run(fixture_doc(WIN))
        assert {c["floor"] for c in r.deck} >= {1, 2, 3}
        assert all(isinstance(c["up"], int) and isinstance(c["ench"], str) for c in r.deck)


class TestParseDamagedEntries:
    def test_a_choice_without_a_card_keeps_the_run(self, doc):
        # schema drift: a reward entry that lost its "card" object used to raise KeyError, and the store then
        # dropped the whole run from the archive with no message anywhere.
        doc["map_point_history"][1][1]["player_stats"][0]["card_choices"] = [
            {"was_picked": True}, {"card": None, "was_picked": False}, None]
        r = parse_run(doc)
        assert r.floors_reached == 49                # the run survives
        assert r.floors[18].cards_picked == [] and r.floors[18].cards_skipped == []

    def test_a_choice_without_a_card_does_not_hide_the_other_choices(self, doc):
        ps = doc["map_point_history"][1][1]["player_stats"][0]
        ps["card_choices"] = [{"was_picked": True}, {"card": {"id": "CARD.BASH"}, "was_picked": True}]
        assert parse_run(doc).floors[18].cards_picked == ["BASH"]

    def test_a_transform_without_both_cards_is_skipped(self, doc):
        ps = doc["map_point_history"][1][1]["player_stats"][0]
        ps["cards_transformed"] = [{"original_card": {"id": "CARD.STRIKE_IRONCLAD"}},
                                   {"original_card": {"id": "CARD.ANGER"}, "final_card": {"id": "CARD.BASH"}}]
        assert parse_run(doc).floors[18].transformed == [("ANGER", "BASH")]

    def test_an_ancient_choice_that_is_not_a_list_does_not_raise(self, doc):
        doc["map_point_history"][0][0]["player_stats"][0]["ancient_choice"] = {"TextKey": "PHIAL_HOLSTER"}
        r = parse_run(doc)
        assert r.floors[0].ancient_pick == "" and r.floors[0].ancient_options == []

    def test_rest_site_choices_that_are_not_a_list_give_an_empty_rest(self, doc):
        doc["map_point_history"][0][6]["player_stats"][0]["rest_site_choices"] = "SMITH"
        assert parse_run(doc).floors[6].rest == ""

    def test_numeric_fields_that_are_not_numbers_do_not_raise(self, doc):
        doc["map_point_history"][0][1]["player_stats"][0].update(current_hp="74", max_hp=None, current_gold=80.4)
        floor = parse_run(doc).floors[1]
        assert floor.hp is None and floor.max_hp is None and floor.gold == 80

    def test_an_entry_that_is_not_a_dict_is_skipped(self, doc):
        doc["map_point_history"][0].insert(1, "not a floor")
        r = parse_run(doc)
        assert r.floors_reached == 49
        assert [f.f for f in r.floors] == list(range(1, 50))

    def test_enchantment_in_the_deck_can_be_a_bare_id(self, doc):
        doc["players"][0]["deck"][0]["enchantment"] = "ENCHANTMENT.SHARP"
        assert parse_run(doc).deck[0]["ench"] == "SHARP"

    def test_a_deck_entry_without_an_id_is_kept_as_empty(self, doc):
        doc["players"][0]["deck"].append({"current_upgrade_level": 1})
        deck = parse_run(doc).deck
        assert deck[-1]["id"] == "" and deck[-1]["up"] == 1
