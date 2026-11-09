"""Smoke test: runs every read-only MCP tool against the fixture runs in a throwaway data folder.

    uv run python tests/smoke.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
home = tempfile.mkdtemp(prefix="sundial-test-")
# hermetic: only the synthetic fixtures, no Steam Cloud saves, no knowledge built from a local game install
os.environ.update(SUNDIAL_HOME=home, STS2_SAVE_ROOT=str(ROOT / "tests" / "fixtures"), STS2_EXTRA_DIRS="",
                  STS2_STEAM_CLOUD="0", STS2_AUTO_KNOWLEDGE="0")
sys.path.insert(0, str(ROOT / "src"))

from sundial_sts2 import server as s  # noqa: E402


def call(tool, **kw):
    fn = getattr(s, tool)
    fn = getattr(fn, "fn", fn)
    out = fn(**kw)
    assert isinstance(out, str) and out.strip(), f"{tool} returned nothing"
    print(f"ok  {tool}({', '.join(f'{k}={v!r}' for k, v in kw.items())})  {len(out)} chars")
    return out


call("status")
call("list_runs")
summary = call("get_run_summary", run="latest")
assert "Victory" in summary, "latest fixture should be the win"
call("get_run_summary", run="latest_death")
call("get_floor", run="latest", floor=17)
call("encounter_history", encounter="Vantom")
call("player_summary", character="IRONCLAD", ascension=10)
call("ascension_climb", character="IRONCLAD")
call("version_summary")
call("list_experts")
call("create_expert", slug="test-expert", name="Test Expert", description="smoke test")
call("set_expert_enabled", slug="test-expert", enabled=True)
call("get_enabled_experts", character="IRONCLAD")
call("save_analysis", run="latest", verdict="v", core_markdown="core",
     experts=[{"slug": "test-expert", "verdict": "x", "markdown": "- ok"}])
assert list((Path(home) / "analyses").glob("*.json")), "analysis not written"
assert len(s.store.runs()) == 3, "smoke test should only see the three fixtures"

# mechanics tagging and the synergy check, on a tiny hand-written knowledge file (no game install needed)
import json  # noqa: E402

from sundial_sts2 import analysis as A  # noqa: E402
from sundial_sts2.mechanics import tag_entry  # noqa: E402

assert tag_entry("Bloodletting", "Lose 3 HP. Gain 2 Energy.") == (["self_damage"], [])
assert tag_entry("Rupture", "Whenever you lose HP on your turn, gain 1 Strength.") == (["strength"], ["self_damage"])
assert tag_entry("Feel No Pain", "Whenever a card is Exhausted, gain 3 Block.") == ([], ["exhaust"])
assert tag_entry("Forgotten Soul", "Whenever you Exhaust a card, deal 1 damage to a random enemy.") == ([], ["exhaust"])
assert "strike" in tag_entry("Pommel Strike", "Deal 9 damage. Draw 1 card.")[0]
kdir = Path(home) / "knowledge"
kdir.mkdir(exist_ok=True)
(kdir / "test.json").write_text(json.dumps([
    {"id": "BLOODLETTING", "kind": "card", "name": "Bloodletting", "text": "Lose 3 HP.", "enables": ["self_damage"]},
    {"id": "BLOOD_WALL", "kind": "card", "name": "Blood Wall", "text": "Lose 2 HP.", "enables": ["self_damage"]},
    {"id": "BRAND", "kind": "card", "name": "Brand", "text": "Lose 1 HP.", "enables": ["self_damage"], "refs": ["Strength"]},
    {"id": "FEEL_NO_PAIN", "kind": "card", "name": "Feel No Pain", "text": "...", "rewards": ["exhaust"]},
    {"id": "STRENGTH", "kind": "power", "name": "Strength", "text": "Strength adds additional damage to Attacks."},
    {"id": "IRONCLAD", "kind": "character", "name": "The Ironclad", "text": "Starts with 80 HP, 99 gold."},
    {"id": "VANTOM_BOSS", "kind": "encounter", "name": "Vantom", "room": "boss", "monsters": ["VANTOM"], "text": "Boss."},
    {"id": "VANTOM", "kind": "monster", "name": "Vantom", "hp": {"base": 173, "asc": 183, "from": 8},
     "moves": [{"id": "INK_BLOT", "name": "Ink Blot", "intents": ["attack"],
                "values": {"InkBlotDamage": {"base": 7, "asc": 8, "from": 9}}}], "text": "HP 173."},
]), encoding="utf-8")
s.kb.reload()
syn = A.synergy_check([{"id": "BLOODLETTING"}, {"id": "BLOOD_WALL"}, {"id": "BRAND"}], [], s.kb)
assert "self_damage" in syn and any("nothing in the deck rewards it" in w for w in A.synergy_warnings(syn, {})), syn
assert "power: Strength" in call("lookup", names=["Strength"])
assert "monster: Vantom" in call("lookup", names=["Vantom"])
win_summary = call("get_run_summary", run="latest_win")
assert "Character (game data): Starts with 80 HP" in win_summary
assert "Vantom 183 HP: Ink Blot (attack; Ink Blot Damage 8)" in win_summary, "A10 run should use the ascension values"
from sundial_sts2.gameworld import at, show  # noqa: E402
assert at({"base": 7, "asc": 8, "from": 9}, 8) == 7 and at({"base": 7, "asc": 8, "from": 9}, 9) == 8
assert show({"base": 7, "asc": 8, "from": 9}) == "7 (8 from A9)"
print("ok  mechanics tagging, synergy check, lookups, enemies at the run's ascension")

# the knowledge layer (card annotations, archetypes): JSON Schema + cross-file checks
import subprocess  # noqa: E402

v = subprocess.run([sys.executable, str(ROOT / "knowledge" / "scripts" / "validate_knowledge.py"), str(ROOT / "knowledge")],
                   capture_output=True, text=True)
assert v.returncode == 0, v.stdout + v.stderr
print("ok  knowledge/ validates")

# archetype detection and role counts (knowledge/SCHEMA.md section 3), on the fixture win
from sundial_sts2.annotations import Annotations  # noqa: E402

snaps = call("get_deck_snapshots", run="latest_win")
assert "| F17 | boss" in snaps and "Knowledge confidence" in snaps, snaps[:500]
summary = call("get_run_summary", run="latest_win")
for part in ("## Deck roles and archetypes at each boss", "## Archetype timeline", "## Knowledge confidence"):
    assert part in summary, part
win = A.resolve(s.store.runs(), "latest_win")
rep = A.archetype_report(win, s.kb, s.ann)
assert rep["has_archetypes"] and rep["bosses"], "Ironclad has archetypes and the win reached bosses"
assert all(v["state"] in ("absent", "forming", "committed", "half_built") for b in rep["bosses"] for v in b["archetypes"].values())
assert "strength" in rep["commit_floor"], rep["commit_floor"]          # Demon Form + Rupture in the fixture win
assert set(rep["confidence"]["draft"]) <= set(rep["confidence"]["annotated"])

# a tiny synthetic knowledge root: states, keystones, support, orphans, staleness
kroot = Path(home) / "ktest"
(kroot / "ironclad").mkdir(parents=True)
(kroot / "SCHEMA.md").write_text("test", encoding="utf-8")
rv = "review: {status: reviewed, build: v0.110.0, by: human}"
(kroot / "ironclad" / "cards.yaml").write_text(f"""schema_version: 1
character: ironclad
cards:
  - {{id: feeder, roles: [], mechanics: [{{tag: exhaust, as: enabler}}], {rv}}}
  - {{id: payoff, roles: [block], mechanics: [{{tag: exhaust, as: payoff}}], {rv}}}
  - {{id: drawer, roles: [draw], {rv}}}
  - {{id: lonely, roles: [], mechanics: [{{tag: strength, as: payoff}}], review: {{status: draft, build: unverified, by: ai}}}}
  - {{id: pump, roles: [scaling], scaling_kind: strength, mechanics: [{{tag: strength, as: enabler}}], {rv}}}
""", encoding="utf-8")
(kroot / "ironclad" / "archetypes.yaml").write_text("""schema_version: 1
character: ironclad
keystone_weight: 2
mechanics: [{tag: exhaust, description: x}, {tag: strength, description: x}]
archetypes:
  - {id: exhaust, name: Exhaust, mechanic: exhaust, keystones: [payoff], thresholds: {committed: {enablers: 2, payoffs: 2}}, support: {draw: 1}}
  - {id: strength, name: Strength, mechanic: strength, thresholds: {committed: {enablers: 1, payoffs: 1}}}
""", encoding="utf-8")
t = Annotations(kroot)
deck = lambda *ids: [{"id": i} for i in ids]
st = lambda *ids: {k: v["state"] for k, v in t.snapshot(deck(*ids), "IRONCLAD", s.kb)["archetypes"].items()}
assert st() == {"exhaust": "absent", "strength": "absent"}
assert st("FEEDER")["exhaust"] == "forming"
assert st("PAYOFF")["exhaust"] == "half_built"              # keystone counts as 2 payoffs, no enablers
sn = t.snapshot(deck("FEEDER", "FEEDER", "PAYOFF"), "IRONCLAD", s.kb)
assert sn["archetypes"]["exhaust"]["state"] == "committed" and not sn["archetypes"]["exhaust"]["support_ok"]
assert sn["primary"] == "exhaust" and sn["roles"]["block"] == 1
assert t.snapshot(deck("FEEDER", "FEEDER", "PAYOFF", "DRAWER"), "IRONCLAD", s.kb)["archetypes"]["exhaust"]["support_ok"]
sn = t.snapshot(deck("FEEDER", "FEEDER", "PAYOFF", "LONELY"), "IRONCLAD", s.kb)
assert [i for i, _ in t.orphans(sn, deck("FEEDER", "FEEDER", "PAYOFF", "LONELY"), s.kb)] == ["LONELY"]
two = deck("FEEDER", "FEEDER", "PAYOFF", "PUMP", "PUMP", "LONELY")       # exhaust E2 P2 = 4, strength E2 P1 = 3
assert t.snapshot(two, "IRONCLAD", s.kb)["primary"] == "exhaust"
assert t.snapshot(two, "IRONCLAD", s.kb, prefer="strength")["primary"] == "strength"      # within the margin: kept
gdir = Path(home) / "knowledge" / "game"
gdir.mkdir(parents=True, exist_ok=True)
card = lambda i, txt: {"id": i, "kind": "card", "name": i.title(), "text": txt}
(gdir / "game-v0.110.0.json").write_text(json.dumps([card("FEEDER", "Exhaust 1 card."), card("PAYOFF", "Old text.")]), encoding="utf-8")
(gdir / "game-v0.111.0.json").write_text(json.dumps([card("FEEDER", "Exhaust 1 card."), card("PAYOFF", "New text.")]), encoding="utf-8")
assert t.review_state("FEEDER", "v0.111.0")["fresh"] == "ok"
assert t.review_state("PAYOFF", "v0.111.0")["fresh"] == "stale"
assert t.review_state("PAYOFF", "v0.110.0")["fresh"] == "ok"              # run not newer than the review
assert t.review_state("PAYOFF", "v0.112.0")["fresh"] == "unchecked"       # no game data for that build
assert t.review_state("LONELY", "v0.111.0")["fresh"] == "unchecked"       # build: unverified
print("ok  archetype states, keystones, support, orphans, primary margin, staleness")

# patch notes (saved beside the game data by the builder)
(gdir / "patch-notes.json").write_text(json.dumps([
    {"date": "2026-07-16", "text": "# Patch\n- Nerfed Vantom: Ink Blot damage lowered"},
    {"date": "2026-08-13", "text": "# Patch\n- Fixed a typo"}]), encoding="utf-8")
assert "2026-07-16: - Nerfed Vantom" in call("patch_notes", query="VANTOM")
assert "2026-08-13" in call("patch_notes") and "Vantom" not in call("patch_notes", query="Vantom", since="2026-08-01")
print("ok  patch notes")
print("\nAll good.")
