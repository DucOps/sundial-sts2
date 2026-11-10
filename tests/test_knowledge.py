"""The knowledge and annotation layers: lookups, the text heuristic, and the shipped knowledge files."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sundial_sts2 import annotations as AN
from sundial_sts2 import knowledge as K
from sundial_sts2.mechanics import MECHANICS, NEEDS_PAYOFF, PAYOFF_MATTERS, label, tag_entry

ROOT = Path(__file__).resolve().parents[1]


def put(kb: K.Knowledge, id_: str, **fields) -> dict:
    """Add one card the way the loader does: keyed by the folded id, and by name."""
    entry = {"id": id_, "kind": "card", **fields}
    kb.entries[("card", K.norm(id_))] = entry
    if entry.get("name"):
        kb.by_name[("card", K.norm(entry["name"]))] = entry
    return entry


class TestKnowledgeLookup:
    def test_norm_folds_ids_names_and_punctuation(self):
        assert K.norm("STRIKE_IRONCLAD") == "STRIKE"          # the five characters' basic cards collapse
        assert K.norm("BASH") == "BASH" and K.norm("bash") == "BASH"
        assert K.norm("Bag Of Marbles") == "BAGOFMARBLES"
        assert K.norm("bag_of_marbles") == "BAGOFMARBLES"

    def test_finds_an_entry_by_id_or_by_name(self, kb):
        kb.entries.clear(), kb.by_name.clear()
        put(kb, "BASH", name="Bash", text="Deal 8 damage.", type="Attack", cost="2", rarity="Basic")
        assert kb.get("card", "bash")["name"] == "Bash"
        assert kb.get("card", "BASH")["name"] == "Bash"
        assert kb.get("card", "Nope") is None

    def test_describe_never_invents_an_effect(self, kb):
        assert kb.describe("card", "NOT_A_CARD") == "Not a Card: (no data; don't guess its effect)"

    def test_describe_shows_type_cost_and_text(self, kb):
        put(kb, "BASH", name="Bash", text="Deal 8 damage.", type="Attack", cost="2", rarity="Basic")
        assert kb.describe("card", "BASH") == "Bash [Attack, 2 energy, Basic]: Deal 8 damage."

    def test_curses_are_known_without_game_data(self, kb):
        assert kb.card_type("ASCENDERS_BANE") == "Curse"
        assert kb.card_type("SOMETHING_ELSE") == "Unknown"

    def test_search_matches_name_and_text(self):
        kb = K.Knowledge()
        kb.entries = {("card", "A"): {"id": "A", "kind": "card", "name": "Alpha", "text": "gains block"},
                      ("card", "B"): {"id": "B", "kind": "card", "name": "Beta", "text": "draws a card"}}
        assert [e["id"] for e in kb.search("block")] == ["A"]
        assert [e["id"] for e in kb.search("beta", "card")] == ["B"]
        assert kb.search("nothing") == []


class TestShippedKnowledge:
    """knowledge/ ships in the wheel as sundial_sts2/annotations; the smoke test validates it against the schema,
    these two checks keep the loader and the files agreeing."""

    def test_every_shipped_annotation_parses_and_has_roles(self, ann):
        assert ann.cards, "no card annotations loaded"
        assert not ann.problems, ann.problems
        for card in ann.cards.values():
            assert card["id"] and isinstance(card.get("roles"), list)

    def test_every_shipped_archetype_has_a_mechanic_and_thresholds(self, ann):
        # a character may use its own vocabulary (SCHEMA.md: block_retention), so a mechanic only has to be
        # declared in that character's own mechanics list — or be one the text tagger knows.
        for character, doc in ann.chars.items():
            declared = {m.get("tag") for m in doc.get("mechanics") or []} | set(MECHANICS)
            for arch in doc.get("archetypes") or []:
                assert arch.get("mechanic") in declared, (character, arch.get("id"))
                assert (arch.get("thresholds") or {}).get("committed") is not None, (character, arch.get("id"))


class TestTextRoles:
    def test_aoe_and_block_come_from_the_text(self, kb):
        put(kb, "THUNDERCLAP", text="Deal 4 damage to ALL enemies.")
        assert AN.text_roles("THUNDERCLAP", kb) == {"aoe"}

    def test_a_power_is_scaling(self, kb):
        put(kb, "INFLAME", type="Power", text="Gain 2 Strength.")
        assert "scaling" in AN.text_roles("INFLAME", kb)

    def test_a_temporary_buff_is_not_scaling(self, kb):
        put(kb, "SETUP_STRIKE", type="Attack", text="Gain 3 Strength this turn.")
        assert "scaling" not in AN.text_roles("SETUP_STRIKE", kb)

    def test_an_unknown_card_has_no_roles(self, kb):
        assert AN.text_roles("NOT_A_CARD", kb) == set()

    @pytest.mark.parametrize("card_id", ["STRIKE_IRONCLAD", "DEFEND_SILENT", "STRIKE", "DEFEND"])
    def test_basics(self, card_id):
        assert AN.is_basic(card_id)

    @pytest.mark.parametrize("card_id", ["POMMEL_STRIKE", "BASH", "DEFEND_THE_WALL"])
    def test_not_basics(self, card_id):
        assert not AN.is_basic(card_id)


class TestMechanicsTagging:
    @pytest.mark.parametrize("name,text,enables,rewards", [
        ("Bloodletting", "Lose 3 HP. Gain 2 Energy.", ["self_damage"], []),
        ("Rupture", "Whenever you lose HP on your turn, gain 1 Strength.", ["strength"], ["self_damage"]),
        ("Feel No Pain", "Whenever a card is Exhausted, gain 3 Block.", [], ["exhaust"]),
        ("Forgotten Soul", "Whenever you Exhaust a card, deal 1 damage to a random enemy.", [], ["exhaust"]),
        ("Pommel Strike", "Deal 9 damage. Draw 1 card.", ["strike"], []),
    ])
    def test_tag_entry(self, name, text, enables, rewards):
        assert tag_entry(name, text) == (enables, rewards)

    def test_a_strike_is_tagged_by_name_not_by_text(self):
        assert "strike" in tag_entry("Twin Strike", "Deal 5 damage twice.")[0]
        assert "strike" in tag_entry("Pommel Strike", "Deal 9 damage. Draw 1 card.")[0]
        assert "strike" not in tag_entry("Strikes of Ruin", "Deal 5 damage.")[0]   # only the exact word counts
        assert "strike" not in tag_entry("Bash", "Deal 8 damage.")[0]

    def test_every_mechanic_has_a_label(self):
        assert all(label(m) for m in MECHANICS)
        assert NEEDS_PAYOFF <= set(MECHANICS) and PAYOFF_MATTERS <= set(MECHANICS)


class TestSnapshot:
    """Role counts and archetype states for one deck (SCHEMA.md §3)."""

    def test_basics_and_curses_are_not_counted(self, ann, kb):
        deck = [{"id": "STRIKE_IRONCLAD"}, {"id": "DEFEND_IRONCLAD"}, {"id": "ASCENDERS_BANE"}]
        snap = ann.snapshot(deck, "IRONCLAD", kb)
        assert snap["size"] == 3 and sum(snap["roles"].values()) == 0

    def test_an_unannotated_card_is_counted_from_its_text_and_marked(self, ann, kb):
        put(kb, "SHIELD_SLAM", name="Shield Slam", text="Deal damage equal to your Block.")
        snap = ann.snapshot([{"id": "SHIELD_SLAM"}], "IRONCLAD", kb)
        assert snap["roles"]["block"] == 1
        assert snap["unannotated"] == ["SHIELD_SLAM"]

    def test_an_annotated_card_uses_its_annotation(self, ann, kb):
        card_id = next(iter(ann.cards))
        snap = ann.snapshot([{"id": card_id}], "IRONCLAD", kb)
        assert snap["unannotated"] == []
        assert sum(snap["roles"].values()) >= 1

    def test_the_primary_archetype_holds_until_another_leads_by_the_margin(self, ann):
        snap = {"archetypes": {}, "roles": {}, "primary": None}
        assert snap["primary"] is None


class TestOrphans:
    def test_a_card_with_no_annotation_is_never_an_orphan(self, ann, kb):
        assert ann.orphans({"archetypes": {}, "roles": {}}, [{"id": "NOT_A_CARD"}], kb) == []


class TestKnowledgeFiles:
    def test_the_shipped_files_are_valid_json_lists(self):
        for f in sorted((ROOT / "knowledge").glob("*/*.yaml")):
            assert f.exists()
        schema = ROOT / "knowledge" / "schema" / "cards.schema.json"
        assert json.loads(schema.read_text(encoding="utf-8"))["type"] == "object"
