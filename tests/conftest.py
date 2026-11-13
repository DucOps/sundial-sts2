"""Shared setup for the pytest suite: everything runs against the synthetic fixtures in a temporary data folder,
never a real archive or game install."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "history"         # save format v10: the three runs everything uses
MODES = ROOT / "tests" / "fixtures" / "modes"               # save format v11: a Fool run and a Blitz run
sys.path.insert(0, str(ROOT / "src"))

WIN = "1790200000.run"          # see tests/fixtures/make_fixtures.py
FOOL = "1790600000.run"
BLITZ = "1790700000.run"


@pytest.fixture
def raw():
    """A fresh copy of one fixture run's JSON, by file name (default: the win), from either fixture folder."""
    cache = {f.name: json.loads(f.read_text(encoding="utf-8")) for d in (FIXTURES, MODES) for f in d.glob("*.run")}
    return lambda name=WIN: copy.deepcopy(cache[name])


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A throwaway Sundial data folder whose save root is an empty folder; returns (home, save_history_dir)."""
    saves = tmp_path / "saves" / "profile1" / "saves" / "history"
    saves.mkdir(parents=True)
    monkeypatch.setenv("SUNDIAL_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("STS2_SAVE_ROOT", str(tmp_path / "saves"))
    monkeypatch.setenv("STS2_EXTRA_DIRS", "")
    monkeypatch.setenv("STS2_STEAM_CLOUD", "0")
    monkeypatch.setenv("STS2_AUTO_KNOWLEDGE", "0")
    monkeypatch.delenv("STS2_ARCHIVE", raising=False)
    return tmp_path / "home", saves
