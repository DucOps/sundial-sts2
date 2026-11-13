"""The parser keeps a run when one entry in it is malformed, and reads every fixture as before."""
import pytest

from sundial_sts2.parse import parse_run, pretty


def _stats(d):
    """Every floor's first player_stats entry."""
    return [pt["player_stats"][0] for act in d["map_point_history"] for pt in act]


def _first(d, key):
    return next(ps for ps in _stats(d) if ps.get(key))


def test_fixture_win_reads_as_before(raw):
    r = parse_run(raw())
    assert r.outcome == "win" and r.character == "IRONCLAD" and r.mode == "standard"
    assert r.floors_reached == len(r.floors) > 40
    assert r.level == "A10"


def test_a_card_choice_without_its_card_costs_only_that_choice(raw):
    d = raw()
    ps = _first(d, "card_choices")
    before = parse_run(raw()).floors
    lost = ps["card_choices"][0]
    del lost["card"]
    r = parse_run(d)
    f = next(f for f, b in zip(r.floors, before) if f.cards_skipped != b.cards_skipped)
    assert len(f.cards_skipped) + len(f.cards_picked) == len(ps["card_choices"]) - 1


@pytest.mark.parametrize("value", [None, "CARD.X", 7, ["CARD.X"]])
def test_card_choices_of_the_wrong_shape(raw, value):
    d = raw()
    _first(d, "card_choices")["card_choices"] = [value]
    assert parse_run(d).outcome == "win"


def test_ancient_choice_as_an_object(raw):
    d = raw()
    ps = _first(d, "ancient_choice")
    ps["ancient_choice"] = {"TextKey": "X", "was_chosen": True}
    i = _stats(d).index(ps)
    f = parse_run(d).floors[i]
    assert f.ancient_pick == "" and f.ancient_options == []


def test_rest_site_choice_as_a_bare_string(raw):
    d = raw()
    _first(d, "rest_site_choices")["rest_site_choices"] = "SMITH"
    assert any(f.rest == "SMITH" for f in parse_run(d).floors)
    assert not any(f.rest == "S" for f in parse_run(d).floors)


def test_nulls_in_player_lists(raw):
    d = raw()
    p = d["players"][0]
    p["potions"] = [None, {"id": "POTION.FIRE_POTION"}]
    p["badges"] = [None]
    p["deck"].append(None)
    p["relics"].append("not an object")
    r = parse_run(d)
    assert r.potions_held == ["FIRE_POTION"] and r.badges == []
    assert len(r.deck) == len(raw()["players"][0]["deck"])


def test_transform_with_a_missing_side(raw):
    d = raw()
    _stats(d)[3]["cards_transformed"] = [{"original_card": {"id": "CARD.STRIKE_IRONCLAD"}}, None]
    assert parse_run(d).floors[3].transformed == [("STRIKE_IRONCLAD", "")]


def test_enchantment_as_id_or_object(raw):
    d = raw()
    _stats(d)[2]["cards_enchanted"] = [{"card": {"id": "CARD.BASH"}, "enchantment": "ENCHANTMENT.SHARP"},
                                       {"card": {"id": "CARD.BASH"}, "enchantment": {"id": "ENCHANTMENT.SHARP"}}]
    assert parse_run(d).floors[2].enchanted == [("BASH", "SHARP")] * 2


@pytest.mark.parametrize("asc,expected", [("7", 7), (None, 0), ("x", 0), (3.0, 3)])
def test_ascension_stored_oddly(raw, asc, expected):
    d = raw()
    d["ascension"] = asc
    assert parse_run(d).ascension == expected


@pytest.mark.parametrize("mode,level", [("standard", "A10"), ("blitz", "Blitz A10"), ("DREAD", "Dread A10"),
                                        (None, "A10"), ("", "A10")])
def test_game_mode(raw, mode, level):
    d = raw()
    d["game_mode"] = mode
    assert parse_run(d).level == level


@pytest.mark.parametrize("raw_id,name", [("CARD.STRIKE_FOOL", "Strike"), ("CARD.DEFEND_FOOL", "Defend"),
                                         ("CARD.STRIKE_IRONCLAD", "Strike"), ("CARD.STRIKE_DUMMY", "Strike Dummy"),
                                         ("ENCOUNTER.PHROG_PARASITE_ELITE", "Phrog Parasite")])
def test_pretty(raw_id, name):
    assert pretty(raw_id) == name
