#!/usr/bin/env python3
"""Generate the synthetic test runs.

tests/fixtures/history: an Ironclad A10 win, a death and an abandoned run (save format v10). The smoke test, the
pytest suite and the demo builds use these three.
tests/fixtures/modes: save format v11 (v0.113): a Fool Standard run that dies to the Act 1 boss, and an Ironclad
Blitz win (fixed 8-floor acts, Neow card picks, merchant services). Only the tests that load them by name use these.

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
OUT_MODES = Path(__file__).resolve().parent / "modes"
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
FOOL_CARDS = {
    "Common": ["ARROW_STAB", "BOW_SMACK", "CHO_FIRM", "DEEP_STRETCH", "HEAVY_SHOT", "JEST", "KI_CHANT", "KI_HOP",
               "KI_WHIP", "NOCK", "QUICK_SHOT", "RAIN_SHOT", "WAH_HAMMER", "WAH_SWEEP"],
    "Uncommon": ["ALL_IS_WELL", "ARCHERY", "CHO_KI", "HIDDEN_ROOTS", "MOTIF", "RHYTHM_STRIKE", "SERRATED_ARROWS",
                 "SONG_PATH", "TIMBER", "TUNE", "WAH_BLAST", "WAH_CHO", "WHISTLING_ARROWS"],
    "Rare": ["CHO_CHORUS", "ENCORE", "FLORESCENCE", "KI_VERSE", "QUIVER", "WAH_CHO_KI", "YAH"],
}
# character: (HP, starter relic, starting deck, card pool)
CHARACTERS = {
    "IRONCLAD": (80, "BURNING_BLOOD", ["STRIKE_IRONCLAD"] * 5 + ["DEFEND_IRONCLAD"] * 4 + ["BASH"], CARDS),
    "FOOL": (77, "SONG_BOW", ["STRIKE_FOOL"] * 5 + ["DEFEND_FOOL"] * 4 + ["FOOLISH_SHOT"], FOOL_CARDS),
}
# Blitz merchant services (blitz_merchant_choices[].type); you take three of the six offered
SERVICES = ["card_removal", "card_rewards", "card_transform", "card_upgrade", "random_upgrades", "rare_card_reward",
            "two_more_choices", "upgraded_rare_card", "prismatic_card_reward"]
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
BLITZ_LAYOUT = {a: "A M M S E T R B" for a in ACTS}        # Blitz: the same 8 rooms every act, 24 floors
TYPES = {"A": "ancient", "M": "monster", "?": "unknown", "S": "shop", "R": "rest_site", "E": "elite",
         "T": "treasure", "B": "boss"}
DAMAGE = {"monster": (2, 16), "elite": (14, 42), "boss": (30, 60)}
TURNS = {"monster": (2, 5), "elite": (4, 7), "boss": (7, 11)}


class Sim:
    def __init__(self, seed: int, start: int, outcome: str, end_floor: int, character: str = "IRONCLAD",
                 ascension: int = 10, mode: str = "standard", schema: int = 10, build: str = BUILD):
        self.rng = random.Random(seed)
        self.start, self.outcome, self.end_floor = start, outcome, end_floor
        self.character, self.ascension, self.mode, self.schema, self.build = character, ascension, mode, schema, build
        hp, relic, deck, self.cards = CHARACTERS[character]
        self.basics = tuple(f"CARD.{c}" for c in deck[:9])          # the Strikes and Defends
        self.hp = self.max_hp = hp
        self.gold, self.floor = 99, 0
        self.deck = [{"floor_added_to_deck": 1, "id": f"CARD.{c}"} for c in deck]
        if ascension >= 5:                                         # A5: start each run Cursed
            self.deck.append({"floor_added_to_deck": 1, "id": "CARD.ASCENDERS_BANE"})
        self.relics = [{"floor_added_to_deck": 1, "id": f"RELIC.{relic}"}]
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
            c = self.rng.choice(self.cards[rar])
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
            heal = min(6, self.max_hp - self.hp) if self.character == "IRONCLAD" else 0     # Burning Blood
            self.hp += heal
            gained = {"monster": self.rng.randint(10, 20), "elite": self.rng.randint(25, 35), "boss": 75}[kind]
            gained = 0 if self.mode == "blitz" else gained          # Blitz: gold stays at 99
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
        if t == "ancient" and self.mode == "blitz" and act == ACTS[0]:
            return self.blitz_neow()
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
        if t == "shop" and self.mode == "blitz":
            return self.blitz_merchant()
        if t == "shop":
            extra: dict = {}
            spent = 0
            if self.gold >= 75:
                removed = next(c for c in self.deck if c["id"] in self.basics)
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
                starters = ("CARD.ASCENDERS_BANE",) + tuple(dict.fromkeys(self.basics))
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

    def blitz_neow(self) -> dict:
        """Blitz Neow: take three cards of eight. The save lists only the five left behind; the three taken are
        in cards_gained."""
        offer = self.rng.sample(sorted(self.cards["Common"] + self.cards["Uncommon"]), 8)
        taken = offer[:3]
        for c in taken:
            self.deck.append({"floor_added_to_deck": self.floor, "id": f"CARD.{c}"})
        st = self.stats(card_choices=[{"card": {"id": f"CARD.{c}"}, "was_picked": False} for c in offer[3:]],
                        cards_gained=[{"id": f"CARD.{c}"} for c in taken],
                        event_choices=[{"title": {"key": "BLITZ.NEOW.title", "table": "ascension"}}])
        return {"map_point_type": "ancient", "player_stats": [st],
                "rooms": [{"model_id": "EVENT.NEOW", "room_type": "event", "turns_taken": 0}]}

    def blitz_merchant(self) -> dict:
        """Blitz merchant: no gold changes hands; you take three of six services."""
        offer = self.rng.sample(SERVICES, 6)
        taken = set(offer[:3]) if "card_rewards" in offer[:3] else set(offer[:2] + ["card_rewards"])
        extra: dict = {"blitz_merchant_choices": [
            {"model_id": "CHARACTER.SILENT" if s == "prismatic_card_reward" else None, "type": s, "was_picked": s in taken}
            for s in dict.fromkeys(offer[:2] + ["card_rewards"] + offer[2:])][:6]}
        extra.update(self.card_reward(0.05))                     # the card_rewards service
        if "card_removal" in taken:
            removed = next(c for c in self.deck if c["id"] in self.basics)
            self.deck.remove(removed)
            extra["cards_removed"] = [removed]
        return {"map_point_type": "shop", "player_stats": [self.stats(**extra)],
                "rooms": [{"room_type": "shop", "turns_taken": 0}]}

    def run(self) -> dict:
        history = []
        for act in ACTS:
            floors = []
            for code in (BLITZ_LAYOUT if self.mode == "blitz" else LAYOUT)[act].split():
                self.floor += 1
                last = self.floor == self.end_floor
                floors.append(self.floor_entry(act, code, last))
                if last:
                    break
            history.append(floors)
            if self.floor >= self.end_floor:
                break
        win = self.outcome == "win"
        out = {
            "acts": ACTS, "ascension": self.ascension, "build_id": self.build, "game_mode": self.mode,
            "killed_by_encounter": self.killer, "killed_by_event": "NONE.NONE", "map_point_history": history,
            "modifiers": [], "platform_type": "steam",
            "players": [{"badges": [], "character": f"CHARACTER.{self.character}", "deck": self.deck, "id": 1,
                         "max_potion_slot_count": 3, "potions": [{"id": p, "slot_index": i} for i, p in enumerate(self.potions)],
                         "relics": self.relics}],
            "run_time": 1500 + self.floor * 60, "schema_version": self.schema,
            "seed": "".join(self.rng.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(12)),
            "start_time": self.start, "was_abandoned": self.outcome == "abandoned", "win": win,
        }
        if self.schema >= 11:
            out["is_custom_game"] = False
        return out


def main() -> None:
    v11 = {"schema": 11, "build": "v0.113.0"}
    sets = {OUT: [Sim(11, 1790000000, "abandoned", 5), Sim(22, 1790100000, "death", 33), Sim(33, 1790200000, "win", 49)],
            OUT_MODES: [Sim(44, 1790600000, "death", 17, character="FOOL", ascension=0, **v11),
                        Sim(55, 1790700000, "win", 24, ascension=1, mode="blitz", **v11)]}
    for out, sims in sets.items():
        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob("*.run"):
            old.unlink()
        for sim in sims:
            run = sim.run()
            (out / f"{sim.start}.run").write_text(json.dumps(run, indent=1), encoding="utf-8")
            print(f"{out.name}/{sim.start}.run  {sim.outcome:9}  floors {sum(map(len, run['map_point_history']))}")


if __name__ == "__main__":
    main()
