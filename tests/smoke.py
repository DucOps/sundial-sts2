"""Smoke test: runs every read-only MCP tool against the fixture runs in a throwaway data folder.

    uv run python tests/smoke.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
home = tempfile.mkdtemp(prefix="sundial-test-")
os.environ.update(SUNDIAL_HOME=home, STS2_SAVE_ROOT=str(ROOT / "tests" / "fixtures"), STS2_EXTRA_DIRS="")
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
print("\nAll good.")
