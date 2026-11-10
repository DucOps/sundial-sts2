"""Shared fixtures: every test runs against the three synthetic runs in tests/fixtures, never a real save folder.

The package reads its settings from the environment at import time, so they are set here, before any test module
imports `sundial_sts2`. `tests/smoke.py` stays as the end-to-end check CLAUDE.md asks for; these tests are the
unit-level suite.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

HOME = Path(tempfile.mkdtemp(prefix="sundial-tests-"))
FIXTURES = ROOT / "tests" / "fixtures"
os.environ.update(SUNDIAL_HOME=str(HOME), STS2_SAVE_ROOT=str(FIXTURES), STS2_EXTRA_DIRS="",
                  STS2_STEAM_CLOUD="0", STS2_AUTO_KNOWLEDGE="0", STS2_ARCHIVE=str(HOME / "archive"))

from sundial_sts2 import analysis as A  # noqa: E402
from sundial_sts2 import server as S  # noqa: E402
from sundial_sts2.knowledge import Knowledge  # noqa: E402
from sundial_sts2.parse import parse_run  # noqa: E402
from sundial_sts2.store import Store  # noqa: E402

ABANDONED, DEATH, WIN = "1790000000", "1790100000", "1790200000"


def fixture_doc(run: str = WIN) -> dict:
    """A fresh copy of one fixture save, safe to mutate."""
    return json.loads((FIXTURES / "history" / f"{run}.run").read_text(encoding="utf-8"))


@pytest.fixture()
def doc() -> dict:
    return fixture_doc()


@pytest.fixture()
def runs() -> list:
    return [parse_run(fixture_doc(r), profile="profile1", file=f"{r}.run") for r in (ABANDONED, DEATH, WIN)]


@pytest.fixture()
def kb() -> Knowledge:
    return Knowledge()


@pytest.fixture()
def ann():
    return S.ann


@pytest.fixture()
def archive(monkeypatch, tmp_path) -> Path:
    """A throwaway archive seeded by syncing the fixture save folder, with the module-level Store reset."""
    monkeypatch.setenv("STS2_ARCHIVE", str(tmp_path / "archive"))
    S.store._cache.clear()
    S.store.problems = {}
    S.store.sync()
    S.store.runs()
    return tmp_path / "archive"


@pytest.fixture()
def experts_dir(monkeypatch, tmp_path) -> Path:
    d = tmp_path / "experts"
    d.mkdir()
    monkeypatch.setenv("SUNDIAL_EXPERTS", str(d))
    (HOME / "config.json").unlink(missing_ok=True)
    return d


@pytest.fixture()
def server_runs(archive) -> list:
    return S.store.runs()
