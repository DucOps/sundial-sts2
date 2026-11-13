"""The knowledge layer: the shipped annotations validate, and the player's own knowledge files win over game data."""
import json
import subprocess
import sys

from conftest import ROOT

from sundial_sts2.knowledge import Knowledge


def test_shipped_knowledge_validates():
    v = subprocess.run([sys.executable, str(ROOT / "knowledge" / "scripts" / "validate_knowledge.py"), str(ROOT / "knowledge")],
                       capture_output=True, text=True)
    assert v.returncode == 0, v.stdout + v.stderr
    assert "0 error(s)" in v.stdout


def test_your_own_files_win_over_game_data(home):
    kdir = home[0] / "knowledge"
    (kdir / "game").mkdir(parents=True)
    (kdir / "game" / "game-v1.json").write_text(json.dumps([
        {"id": "BASH", "kind": "card", "name": "Bash", "text": "from the game"},
        {"id": "ANGER", "kind": "card", "name": "Anger", "text": "game only"}]), encoding="utf-8")
    (kdir / "game" / "current.json").write_text(json.dumps({"file": "game-v1.json"}), encoding="utf-8")
    (kdir / "mine.json").write_text(json.dumps([{"id": "BASH", "kind": "card", "name": "Bash", "text": "my note"}]),
                                    encoding="utf-8")
    kb = Knowledge()
    assert kb.get("card", "BASH")["text"] == "my note"
    assert kb.get("card", "ANGER")["text"] == "game only"
    assert kb.loaded_from[-1].endswith("mine.json")


def test_bad_files_are_skipped(home):
    kdir = home[0] / "knowledge"
    kdir.mkdir(parents=True)
    (kdir / "broken.json").write_text("{not json", encoding="utf-8")
    (kdir / "object.json").write_text('{"id": "X"}', encoding="utf-8")
    kb = Knowledge()
    assert kb.get("card", "X") is None
