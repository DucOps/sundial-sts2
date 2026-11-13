"""Save format v11 (v0.113): The Fool, Blitz (Neow card picks, merchant services) and custom games, read the same
way by both parsers."""
import json
import shutil
import subprocess

import pytest
from conftest import BLITZ, FIXTURES, FOOL, MODES, ROOT

from sundial_sts2 import analysis as A
from sundial_sts2.knowledge import Knowledge
from sundial_sts2.parse import parse_run


def _floors(d):
    return [pt for act in d["map_point_history"] for pt in act]


def test_the_fool(raw):
    r = parse_run(raw(FOOL))
    assert r.character == "FOOL" and r.level == "A0" and r.outcome == "death" and r.killer == "VANTOM_BOSS"
    assert {"STRIKE_FOOL", "DEFEND_FOOL", "FOOLISH_SHOT"} <= {c["id"] for c in r.deck}


def test_blitz_layout(raw):
    r = parse_run(raw(BLITZ))
    assert r.mode == "blitz" and r.level == "Blitz A1" and r.outcome == "win"
    assert "".join(f.t for f in r.floors) == "AHHSETRB" * 3


def test_blitz_neow_picks_are_the_cards_gained(raw):
    d = raw(BLITZ)
    ps = _floors(d)[0]["player_stats"][0]
    f = parse_run(d).floors[0]
    assert f.cards_picked == [c["id"].split(".", 1)[1] for c in ps["cards_gained"]] and len(f.cards_picked) == 3
    assert len(f.cards_skipped) == 5 and f.gained_other == [] and f.events == ["Neow"]


def test_choose_n_events_outside_blitz(raw):
    """Room Full of Cheese, Brain Leech: the save lists the cards left behind; the ones taken are cards gained."""
    d = raw()
    pt = _floors(d)[3]                                    # an event in the fixture win
    pt["rooms"] = [{"model_id": "EVENT.ROOM_FULL_OF_CHEESE", "room_type": "event", "turns_taken": 0}]
    pt["player_stats"][0].update(card_choices=[{"card": {"id": f"CARD.{c}"}, "was_picked": False} for c in ("ANGER", "TAUNT")],
                                 cards_gained=[{"id": "CARD.HEADBUTT"}, {"id": "CARD.TRUE_GRIT"}])
    f = parse_run(d).floors[3]
    assert f.cards_picked == ["HEADBUTT", "TRUE_GRIT"] and f.gained_other == [] and A._is_reward(f)


def test_an_ancient_relic_choice_is_not_a_skip(raw):
    """Hefty Tablet and the like: no pick is marked and the gained cards include a curse, so nothing is inferred,
    but the floor isn't counted as a skipped reward either."""
    d = raw()
    ps = _floors(d)[0]["player_stats"][0]                 # Neow, with an Ancient relic chosen
    ps.update(card_choices=[{"card": {"id": "CARD.CRUELTY"}, "was_picked": False}],
              cards_gained=[{"id": "CARD.DEMON_FORM"}, {"id": "CARD.INJURY"}])
    f = parse_run(d).floors[0]
    assert f.ancient_pick and f.cards_picked == [] and f.gained_other == ["DEMON_FORM", "INJURY"]
    assert not A._is_reward(f)


def test_a_question_mark_room_that_was_a_shop(raw):
    d = raw()
    pt = _floors(d)[3]
    pt["rooms"] = [{"room_type": "shop", "turns_taken": 0}]
    pt["player_stats"][0].update(card_choices=[{"card": {"id": "CARD.ANGER"}, "was_picked": False}], gold_spent=75)
    r = parse_run(d)
    f = r.floors[3]
    out = A.digest([r], r, Knowledge())
    assert f.t == "?" and f.room == "shop" and not A._is_reward(f)
    assert "F4  A1 ? | ? room: shop, spent 75g" in out and "other cards in stock: Anger" in out


def test_a_fight_without_the_usual_suffix(raw):
    d = raw()
    _floors(d)[1]["rooms"][0]["model_id"] = "ENCOUNTER.OVERGROWTH_CRAWLERS"
    r = parse_run(d)
    assert r.floors[1].encounter == "OVERGROWTH_CRAWLERS"
    assert A.encounter_stats([r], "OVERGROWTH_CRAWLERS")["fought"] == 1


def test_blitz_merchant(raw):
    r = parse_run(raw(BLITZ))
    shops = [f for f in r.floors if f.t == "S"]
    assert len(shops) == 3 and all(f.merchant for f in shops)
    assert all(len(f.services_picked) == 3 and len(f.services_skipped) == 3 for f in shops)
    assert any(s.startswith("prismatic_card_reward:") for f in shops for s in f.services_picked + f.services_skipped)
    assert all(A._is_reward(f) for f in shops)          # its card choices are rewards, not shop stock


def test_blitz_summary(raw):
    r = parse_run(raw(BLITZ))
    out = A.digest([r], r, Knowledge())
    assert out.startswith("# Run 1790700000: Ironclad Blitz A1")
    assert "merchant: took " in out and "Prismatic Card Reward (Silent)" in out
    assert "other cards in stock" not in out and "bought nothing" not in out
    assert "F1  A1 A | Neow | " in out and "skipped cards" not in out.split("F2 ")[0].split("F1 ")[-1]
    assert "at A0–A2" in out


def test_a_standard_shop_still_lists_stock(raw):
    r = parse_run(raw())
    d = raw()
    ps = _floors(d)[5]["player_stats"][0]
    ps["card_choices"] = [{"card": {"id": "CARD.ANGER"}, "was_picked": False}]
    r = parse_run(d)
    assert r.floors[5].t == "S" and not r.floors[5].merchant and not A._is_reward(r.floors[5])
    assert "other cards in stock: Anger" in A.digest([r], r, Knowledge())


def test_no_baseline_range_starts_at_a0(raw):
    r = parse_run(raw(FOOL))
    assert "at A0–A1" in A.peers([r], r)[1]


def test_custom_games_are_kept_apart(raw):
    std, d = parse_run(raw()), raw()
    d["start_time"], d["is_custom_game"] = 1790300000, True
    cus = parse_run(d)
    assert cus.custom and cus.bucket == "custom" and cus.level == "Custom A10"
    runs = [std, cus]
    assert A.peers(runs, std)[0] == [] and A.peers(runs, cus)[0] == []
    assert A.player_summary(runs, "IRONCLAD", None, None).startswith("# 1 runs")
    assert A.player_summary(runs, "IRONCLAD", None, None, mode="custom").startswith("# 1 runs")
    assert A.player_summary(runs, "IRONCLAD", None, None, mode="all").startswith("# 2 runs")
    assert "Custom runs" in A.climb(runs, "IRONCLAD", "custom")
    assert A.check_mode("Custom") == "custom"


def test_is_custom_game_must_be_true(raw):
    for v in (False, None, "true", 1):
        d = raw()
        d["is_custom_game"] = v
        assert not parse_run(d).custom


NODE = shutil.which("node")


@pytest.mark.skipif(not NODE, reason="node isn't installed")
def test_both_parsers_agree():
    """web/src/parse.js and parse.py read the same picks, skips and merchant services from every fixture."""
    script = """
const S = require(process.argv[1]), fs = require('fs');
const out = {};
for (const f of process.argv.slice(2)) {
  const r = S.parseRun(JSON.parse(fs.readFileSync(f, 'utf8')), {});
  out[f] = { mode: r.mode, custom: r.custom, offers: r.offers.length,
             floors: r.path.map(p => [p.t, p.cp, p.cs, !!p.mer, p.svp, p.svs, p.ev, p.room, p.enc]) };
}
console.log(JSON.stringify(out));"""
    files = sorted(str(f) for d in (FIXTURES, MODES) for f in d.glob("*.run"))
    js = json.loads(subprocess.run([NODE, "-e", script, str(ROOT / "web" / "src" / "parse.js"), *files],
                                   capture_output=True, text=True, check=True).stdout)
    for f in files:
        r = parse_run(json.loads(open(f, encoding="utf-8").read()))
        py = {"mode": r.mode, "custom": r.custom, "offers": sum(A._is_reward(x) for x in r.floors),
              "floors": [[x.t, x.cards_picked, x.cards_skipped, x.merchant, x.services_picked, x.services_skipped,
                          x.events, x.room, x.encounter] for x in r.floors]}
        assert js[f] == py, f


def test_dread_hp_bonus_is_kept_apart():
    """v0.113 boss HP: GetValueIfAscension(...) + (IsDread() ? n : 0). Only Dread runs add n."""
    from sundial_sts2.gameworld import monster_line
    m = {"name": "The Insatiable", "hp": {"base": 321, "asc": 341, "from": 8}, "dread_hp_bonus": 20, "moves": []}
    assert monster_line(m, 0) == "The Insatiable 321 HP" and monster_line(m, 10) == "The Insatiable 341 HP"
    assert monster_line(m, 10, dread=True) == "The Insatiable 361 HP"


def test_blitz_player_summary_lists_services_and_neow(raw):
    r = parse_run(raw(BLITZ))
    out = A.player_summary([r], "IRONCLAD", None, None, mode="blitz")
    assert "Blitz merchant services you take" in out and "Card Rewards 3/3" in out
    assert "Blitz Neow cards you took" in out
    assert "Blitz merchant" not in A.player_summary([r], "IRONCLAD", None, None, mode="all")
