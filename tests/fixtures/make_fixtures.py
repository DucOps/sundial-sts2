#!/usr/bin/env python3
"""Generate the three synthetic test runs in tests/fixtures/history: an Ironclad A10 win, a death and an abandoned run.

The runs are built from scratch with a fixed random seed, using only game content names (cards, relics, encounters,
events). No real player's run is copied, so the fixtures (and the demo data and screenshots made from them) contain
nobody's play history. Re-run after changing the generator; the output is the same every time.

    python tests/fixtures/make_fixtures.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "history"
BUILD = "v0.111.0"

CARDS = {
    "Common": ["ANGER", "ARMAMENTS", "BLOOD_WALL", "BODY_SLAM", "BREAKTHROUGH", "HEADBUTT", "IRON_WAVE", "MOLTEN_FIST",
               "PERFECTED_STRIKE", "POMMEL_STRIKE", "SHRUG_IT_OFF", "SWORD_BOOMERANG", "TAUNT", "THUNDERCLAP",
               "TREMBLE", "TRUE_GRIT", "TWIN_STRIKE"],
    "Uncommon": ["BATTLE_TRANCE", "BLOODLETTING", "BLUDGEON", "BURNING_PACT", "COLOSSUS", "CRUELTY", "DRUM_OF_BATTLE",
                 "FEEL_NO_PAIN", "FLAME_BARRIER", "HEMOKINESIS", "HOWL_FROM_BEYOND", "INFERNO", "INFLAME", "RAMPAGE",
                 "RUPTURE", "SECOND_WIND", "STOMP", "STONE_ARMOR", "UNRELENTING", "UPPERCUT", "WHIRLWIND"],
    "Rare": ["BARRICADE", "BRAND", "CRIMSON_MANTLE", "DARK_EMBRACE", "DEMON_FORM", "DOMINATE", "FIEND_FIRE",
             "IMPERVIOUS", "OFFERING", "TEAR_ASUNDER", "THRASH"],
}
RELICS = ["AKABEKO", "ANCHOR", "BAG_OF_MARBLES", "BAG_OF_PREPARATION", "BLOOD_VIAL", "BRONZE_SCALES",
          "CENTENNIAL_PUZZLE", "HAPPY_FLOWER", "LANTERN", "LETTER_OPENER", "MEAL_TICKET", "NUNCHAKU",
          "ODDLY_SMOOTH_STONE", "ORICHALCUM", "ORNAMENTAL_FAN", "PEN_NIB", "PENDULUM", "POTION_BELT", "RED_MASK",
          "VAJRA", "KUNAI", "GAMBLING_CHIP", "ART_OF_WAR", "TUNGSTEN_ROD"]
ANCIENT_RELICS = {"EVENT.NEOW": ["PHIAL_HOLSTER", "SILVER_CRUCIBLE", "BOOMING_CONCH", "NEOWS_TALISMAN"],
                  "EVENT.TEZCATARA": ["VERY_HOT_COCOA", "TOASTY_MITTENS", "TOY_BOX"],
                  "EVENT.NONUPEIPE": ["JEWELRY_BOX", "FUR_COAT", "BEAUTIFUL_BRACELET"]}
POTIONS = ["ATTACK_POTION", "BLOCK_POTION", "BLOOD_POTION", "EXPLOSIVE_AMPOULE", "FIRE_POTION", "FLEX_POTION",
           "POWER_POTION", "SKILL_POTION", "STRENGTH_POTION", "SWIFT_POTION", "WEAK_POTION"]
ACTS = ["ACT.OVERGROWTH", "ACT.HIVE", "ACT.GLORY"]
ENCOUNTERS = {
    "ACT.OVERGROWTH": {
        "monster": {"NIBBITS_WEAK": ["NIBBIT"], "SHRINKER_BEETLE_WEAK": ["SHRINKER_BEETLE"],
                    "FUZZY_WURM_CRAWLER_WEAK": ["FUZZY_WURM_CRAWLER"], "FOGMOG_NORMAL": ["FOGMOG"],
                    "VINE_SHAMBLER_NORMAL": ["VINE_SHAMBLER"], "SNAPPING_JAXFRUIT_NORMAL": ["SNAPPING_JAXFRUIT"]},
        "elite": {"PHROG_PARASITE_ELITE": ["PHROG_PARASITE", "WRIGGLER"], "BYRDONIS_ELITE": ["BYRDONIS"]},
        "boss": {"VANTOM_BOSS": ["VANTOM"]},
    },
    "ACT.HIVE": {
        "monster": {"TUNNELER_WEAK": ["TUNNELER"], "EXOSKELETONS_WEAK": ["EXOSKELETON"],
                    "THIEVING_HOPPER_WEAK": ["THIEVING_HOPPER"], "CHOMPERS_NORMAL": ["CHOMPER"],
                    "THE_OBSCURA_NORMAL": ["THE_OBSCURA", "PARAFRIGHT"]},
        "elite": {"ENTOMANCER_ELITE": ["ENTOMANCER"], "INFESTED_PRISMS_ELITE": ["INFESTED_PRISM"]},
        "boss": {"KNOWLEDGE_DEMON_BOSS": ["KNOWLEDGE_DEMON"]},
    },
    "ACT.GLORY": {
        "monster": {"SCROLLS_OF_BITING_WEAK": ["SCROLL_OF_BITING"], "DEVOTED_SCULPTOR_WEAK": ["DEVOTED_SCULPTOR"],
                    "FABRICATOR_NORMAL": ["FABRICATOR"], "GLOBE_HEAD_NORMAL": ["GLOBE_HEAD"]},
        "elite": {"MECHA_KNIGHT_ELITE": ["MECHA_KNIGHT"], "KNIGHTS_ELITE": ["FLAIL_KNIGHT", "SPECTRAL_KNIGHT"]},
        "boss": {"QUEEN_BOSS": ["QUEEN"], "AEONGLASS_BOSS": ["AEONGLASS"]},
    },
}
EVENTS = {"ACT.OVERGROWTH": ["SUNKEN_STATUE", "WELLSPRING", "WOOD_CARVINGS", "THIS_OR_THAT"],
          "ACT.HIVE": ["SYMBIOTE", "STONE_OF_ALL_TIME", "FIELD_OF_MAN_SIZED_HOLES", "COLORFUL_PHILOSOPHERS"],
          "ACT.GLORY": ["ROUND_TEA_PARTY", "REFLECTIONS", "SLIPPERY_BRIDGE", "RANWID_THE_ELDER"]}
ANCIENTS = {"ACT.OVERGROWTH": "EVENT.NEOW", "ACT.HIVE": "EVENT.TEZCATARA", "ACT.GLORY": "EVENT.NONUPEIPE"}
# room order per act (an ancient first; Act 3 ends with the A10 double boss)
LAYOUT = {
    "ACT.OVERGROWTH": "A M M ? M S R E ? T M R E ? M R B",
    "ACT.HIVE": "A M ? M S M R E T ? E M R M R B",          # floors 18-33
    "ACT.GLORY": "A M ? S M R E T ? M R E M R B B",         # floors 34-49
}
TYPES = {"A": "ancient", "M": "monster", "?": "unknown", "S": "shop", "R": "rest_site", "E": "elite",
         "T": "treasure", "B": "boss"}
DAMAGE = {"monster": (2, 16), "elite": (14, 42), "boss": (30, 60)}
TURNS = {"monster": (2, 5), "elite": (4, 7), "boss": (7, 11)}


class Sim:
    def __init__(self, seed: int, start: int, outcome: str, end_floor: int):
        self.rng = random.Random(seed)
        self.start, self.outcome, self.end_floor = start, outcome, end_floor
        self.hp = self.max_hp = 80
        self.gold, self.floor = 99, 0
        self.deck = [{"floor_added_to_deck": 1, "id": "CARD.STRIKE_IRONCLAD"} for _ in range(5)]
        self.deck += [{"floor_added_to_deck": 1, "id": "CARD.DEFEND_IRONCLAD"} for _ in range(4)]
        self.deck += [{"floor_added_to_deck": 1, "id": "CARD.BASH"}, {"floor_added_to_deck": 1, "id": "CARD.ASCENDERS_BANE"}]
        self.relics = [{"floor_added_to_deck": 1, "id": "RELIC.BURNING_BLOOD"}]
        self.potions: list[str] = []
        self.killer = "NONE.NONE"

    def stats(self, **extra) -> dict:
        s = {"current_gold": self.gold, "current_hp": max(self.hp, 0), "damage_taken": 0, "gold_gained": 0,
             "gold_lost": 0, "gold_spent": 0, "gold_stolen": 0, "hp_healed": 0, "is_affected_by_fur_coat": False,
             "max_hp": self.max_hp, "max_hp_gained": 0, "max_hp_lost": 0, "player_id": 1, "stolen_loot": 0}
        s.update(extra)
        return s

    def card_reward(self, rare_chance: float) -> dict:
        pool = [r for r in ("Common", "Uncommon", "Rare") for _ in range({"Common": 6, "Uncommon": 3, "Rare": 1}[r])]
        offer: list[str] = []
        while len(offer) < 3:
            rar = "Rare" if self.rng.random() < rare_chance else self.rng.choice(pool)
            c = self.rng.choice(CARDS[rar])
            if c not in offer:
                offer.append(c)
        pick = None if self.rng.random() < 0.15 else self.rng.randrange(3)
        choices = []
        for i, c in enumerate(offer):
            card = {"id": f"CARD.{c}"}
            if i == pick:
                card = {"floor_added_to_deck": self.floor, "id": f"CARD.{c}"}
                self.deck.append(dict(card))
            choices.append({"card": card, "was_picked": i == pick})
        out = {"card_choices": choices}
        if pick is not None:
            out["cards_gained"] = [{"id": f"CARD.{offer[pick]}"}]
        return out

    def relic(self, pool=RELICS) -> str:
        have = {r["id"] for r in self.relics}
        r = self.rng.choice([x for x in pool if f"RELIC.{x}" not in have])
        self.relics.append({"floor_added_to_deck": self.floor, "id": f"RELIC.{r}"})
        return f"RELIC.{r}"

    def fight(self, act: str, kind: str, last: bool) -> dict:
        enc, mons = self.rng.choice(sorted(ENCOUNTERS[act][kind].items()))
        if kind == "boss" and act == "ACT.GLORY":          # double boss: Queen, then Aeonglass
            enc, mons = list(ENCOUNTERS[act][kind].items())[int(self.floor == 49)]
        lo, hi = DAMAGE[kind]
        dmg = self.rng.randint(lo, hi)
        extra: dict = {}
        if self.potions and (kind != "monster" or self.rng.random() < 0.2):
            used = self.potions.pop(0)
            extra["potion_used"] = [used]
            dmg = max(0, dmg - 8)
        dies = last and self.outcome == "death"
        if dies:
            dmg = self.hp
        elif dmg >= self.hp:
            dmg = self.hp - self.rng.randint(3, 9)
        self.hp -= dmg
        heal = 0
        if not dies:
            heal = min(6, self.max_hp - self.hp)           # Burning Blood
            self.hp += heal
            gained = {"monster": self.rng.randint(10, 20), "elite": self.rng.randint(25, 35), "boss": 75}[kind]
            self.gold += gained
            extra["gold_gained"] = gained
            if kind != "boss" or act != "ACT.GLORY":
                extra.update(self.card_reward(0.3 if kind == "elite" else 0.05))
            if kind == "elite":
                extra["relic_choices"] = [{"choice": self.relic(), "was_picked": True}]
            if self.rng.random() < 0.35 and len(self.potions) < 3:
                p = f"POTION.{self.rng.choice(POTIONS)}"
                self.potions.append(p)
                extra["potion_choices"] = [{"choice": p, "was_picked": True}]
        else:
            self.killer = f"ENCOUNTER.{enc}"
        room = {"model_id": f"ENCOUNTER.{enc}", "monster_ids": [f"MONSTER.{m}" for m in mons], "room_type": kind,
                "turns_taken": self.rng.randint(*TURNS[kind])}
        return {"map_point_type": kind, "player_stats": [self.stats(damage_taken=dmg, hp_healed=heal, **extra)],
                "rooms": [room]}

    def floor_entry(self, act: str, code: str, last: bool) -> dict:
        t = TYPES[code]
        if t in DAMAGE:
            return self.fight(act, t, last)
        if t == "ancient":
            anc = ANCIENTS[act]
            opts = ANCIENT_RELICS[anc][:3]
            pick = self.rng.randrange(len(opts))
            self.relics.append({"floor_added_to_deck": self.floor, "id": f"RELIC.{opts[pick]}"})
            heal = self.max_hp - self.hp if act != ACTS[0] else 0
            self.hp += heal
            st = self.stats(hp_healed=heal, ancient_choice=[
                {"TextKey": o, "title": {"key": f"{o}.title", "table": "relics"}, "was_chosen": i == pick}
                for i, o in enumerate(opts)],
                event_choices=[{"title": {"key": f"{opts[pick]}.title", "table": "relics"}}],
                relic_choices=[{"choice": f"RELIC.{opts[pick]}", "was_picked": True}])
            return {"map_point_type": "ancient", "player_stats": [st],
                    "rooms": [{"model_id": anc, "room_type": "event", "turns_taken": 0}]}
        if t == "unknown":
            ev = self.rng.choice(EVENTS[act])
            st = self.stats(event_choices=[{"title": {"key": f"{ev}.pages.INITIAL.options.ACCEPT.title",
                                                      "table": "events"}}])
            return {"map_point_type": "unknown", "player_stats": [st],
                    "rooms": [{"model_id": f"EVENT.{ev}", "room_type": "event", "turns_taken": 0}]}
        if t == "shop":
            extra: dict = {}
            spent = 0
            if self.gold >= 75:
                removed = next(c for c in self.deck if c["id"] in ("CARD.STRIKE_IRONCLAD", "CARD.DEFEND_IRONCLAD"))
                self.deck.remove(removed)
                extra["cards_removed"] = [removed]
                spent += 75
            if self.gold - spent >= 150:
                extra["bought_relics"] = [self.relic()]
                extra["relic_choices"] = [{"choice": extra["bought_relics"][0], "was_picked": True}]
                spent += 150
            self.gold -= spent
            return {"map_point_type": "shop", "player_stats": [self.stats(gold_spent=spent, **extra)],
                    "rooms": [{"room_type": "shop", "turns_taken": 0}]}
        if t == "rest_site":
            if self.hp < self.max_hp * 0.6:
                heal = min(int(self.max_hp * 0.3), self.max_hp - self.hp)
                self.hp += heal
                st = self.stats(hp_healed=heal, rest_site_choices=["HEAL"])
            else:
                starters = ("CARD.ASCENDERS_BANE", "CARD.STRIKE_IRONCLAD", "CARD.DEFEND_IRONCLAD")
                up = next((c for c in reversed(self.deck) if c["id"] not in starters
                           and not c.get("current_upgrade_level")),
                          next(c for c in self.deck if c["id"] != "CARD.ASCENDERS_BANE"))
                up["current_upgrade_level"] = 1
                st = self.stats(rest_site_choices=["SMITH"], upgraded_cards=[up["id"]])
            return {"map_point_type": "rest_site", "player_stats": [st],
                    "rooms": [{"room_type": "rest_site", "turns_taken": 0}]}
        # treasure
        st = self.stats(relic_choices=[{"choice": self.relic(), "was_picked": True}])
        return {"map_point_type": "treasure", "player_stats": [st], "rooms": [{"room_type": "treasure", "turns_taken": 0}]}

    def run(self) -> dict:
        history = []
        for act in ACTS:
            floors = []
            for code in LAYOUT[act].split():
                self.floor += 1
                last = self.floor == self.end_floor
                floors.append(self.floor_entry(act, code, last))
                if last:
                    break
            history.append(floors)
            if self.floor >= self.end_floor:
                break
        win = self.outcome == "win"
        return {
            "acts": ACTS, "ascension": 10, "build_id": BUILD, "game_mode": "standard",
            "killed_by_encounter": self.killer, "killed_by_event": "NONE.NONE", "map_point_history": history,
            "modifiers": [], "platform_type": "steam",
            "players": [{"badges": [], "character": "CHARACTER.IRONCLAD", "deck": self.deck, "id": 1,
                         "max_potion_slot_count": 3, "potions": [{"id": p, "slot_index": i} for i, p in enumerate(self.potions)],
                         "relics": self.relics}],
            "run_time": 1500 + self.floor * 60, "schema_version": 10,
            "seed": "".join(self.rng.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(12)),
            "start_time": self.start, "was_abandoned": self.outcome == "abandoned", "win": win,
        }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.run"):
        old.unlink()
    specs = [(11, 1790000000, "abandoned", 5), (22, 1790100000, "death", 33), (33, 1790200000, "win", 49)]
    for seed, start, outcome, end in specs:
        run = Sim(seed, start, outcome, end).run()
        (OUT / f"{start}.run").write_text(json.dumps(run, indent=1), encoding="utf-8")
        print(f"{start}.run  {outcome:9}  floors {sum(map(len, run['map_point_history']))}")


if __name__ == "__main__":
    main()
