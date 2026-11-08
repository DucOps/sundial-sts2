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
]), encoding="utf-8")
s.kb.reload()
syn = A.synergy_check([{"id": "BLOODLETTING"}, {"id": "BLOOD_WALL"}, {"id": "BRAND"}], [], s.kb)
assert "self_damage" in syn and any("nothing in the deck rewards it" in w for w in A.synergy_warnings(syn, {})), syn
assert "power: Strength" in call("lookup", names=["Strength"])
print("ok  mechanics tagging, synergy check, power lookup")
print("\nAll good.")
