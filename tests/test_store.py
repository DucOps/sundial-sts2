"""The store: archiving new runs, and never losing one without saying why."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from conftest import ABANDONED, DEATH, WIN, fixture_doc
from sundial_sts2.store import Store, archive_dir, source_dirs


def _write(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")
    return path


class TestSync:
    def test_copies_the_fixture_runs_into_the_archive(self, archive):
        files = sorted(p.name for p in archive.rglob("*.run"))
        assert files == [f"{r}.run" for r in (ABANDONED, DEATH, WIN)]
        assert {p.parent.name for p in archive.rglob("*.run")} == {"profile1"}

    def test_a_second_sync_copies_nothing_new(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STS2_ARCHIVE", str(tmp_path / "arch"))
        store = Store()
        first = store.sync()
        second = store.sync()
        assert first["added"] == 3 and first["scanned"] == 3
        assert second["added"] == 0 and second["updated"] == 0

    def test_keeps_the_profile_from_the_save_path(self, archive, tmp_path, monkeypatch):
        src = tmp_path / "saves"
        _write(src / "profile3" / "saves" / "history" / "1790400000.run", fixture_doc())
        monkeypatch.setenv("STS2_SAVE_ROOT", str(src))
        monkeypatch.setenv("STS2_ARCHIVE", str(tmp_path / "other"))
        store = Store()
        store.sync()
        assert (tmp_path / "other" / "profile3" / "1790400000.run").exists()

    def test_ignores_run_files_outside_a_history_folder(self, tmp_path, monkeypatch):
        src = tmp_path / "saves"
        _write(src / "history" / "1790500000.run", fixture_doc())
        _write(src / "elsewhere" / "1790600000.run", fixture_doc())
        monkeypatch.setenv("STS2_SAVE_ROOT", str(src))
        monkeypatch.setenv("STS2_ARCHIVE", str(tmp_path / "arch"))
        store = Store()
        assert store.sync()["added"] == 1

    def test_a_newer_source_file_replaces_the_archived_copy(self, archive, tmp_path, monkeypatch):
        src = tmp_path / "saves"
        run = _write(src / "history" / "1790700000.run", fixture_doc())
        monkeypatch.setenv("STS2_SAVE_ROOT", str(src))
        monkeypatch.setenv("STS2_ARCHIVE", str(tmp_path / "arch"))
        store = Store()
        store.sync()
        dest = tmp_path / "arch" / "profile1" / "1790700000.run"
        os.utime(dest, (1, 1))
        os.utime(run, (100, 100))
        assert store.sync()["updated"] == 1

    def test_reports_the_sources_and_the_archive_it_used(self, archive):
        info = Store().sync()
        assert info["archive"] == str(archive)
        assert all(Path(p).exists() for p in info["sources"])


class TestRuns:
    def test_loads_every_archived_run_oldest_first(self, archive):
        store = Store()
        store.sync()
        runs = store.runs()
        assert [r.id for r in runs] == [1790000000, 1790100000, 1790200000]
        assert [r.outcome for r in runs] == ["abandoned", "death", "win"]

    def test_reuses_the_parsed_run_until_the_file_changes(self, archive):
        store = Store()
        store.sync()
        assert store.runs()[0] is store.runs()[0]          # cached, not re-parsed
        f = next(archive.rglob("1790000000.run"))
        doc = fixture_doc(ABANDONED)
        doc["run_time"] = 1800
        _write(f, doc)
        os.utime(f, (9_999_999_999, 9_999_999_999))
        assert store.runs()[0].duration == 1800

    def test_a_deleted_file_leaves_the_list(self, archive):
        store = Store()
        store.sync()
        next(archive.rglob("1790000000.run")).unlink()
        assert [r.id for r in store.runs()] == [1790100000, 1790200000]
        assert store.unreadable() == {}

    def test_no_archive_is_an_empty_list_not_an_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STS2_ARCHIVE", str(tmp_path / "missing"))
        store = Store()
        assert store.runs() == [] and store.unreadable() == {}


class TestUnreadableRuns:
    """The archive is the only copy of a run the game has already pruned: a file that cannot be read must be
    reported, never silently dropped."""

    def test_a_half_filled_reward_no_longer_costs_the_run(self, archive):
        doc = fixture_doc(DEATH)
        doc["start_time"] = 1790300000
        doc["map_point_history"][0][1]["player_stats"][0]["card_choices"] = [{"was_picked": True}]
        _write(archive / "profile1" / "1790300000.run", doc)
        store = Store()
        store.sync()
        assert 1790300000 in [r.id for r in store.runs()]
        assert store.unreadable() == {}

    @pytest.mark.parametrize("payload,reason", [
        ("{not json", "JSONDecodeError"),
        ("[]", "not a run history file"),
        (json.dumps({"hello": "world"}), "not a run history file"),
    ])
    def test_an_unreadable_file_is_reported_with_its_reason(self, archive, payload, reason):
        _write(archive / "profile1" / "1790999999.run", payload)
        store = Store()
        store.runs()
        problems = store.unreadable()
        assert list(problems) == ["profile1/1790999999.run"]
        assert reason in problems["profile1/1790999999.run"]

    def test_one_unreadable_file_never_costs_the_others(self, archive):
        _write(archive / "profile1" / "1790888888.run", "{")
        store = Store()
        assert len(store.runs()) == 3
        assert len(store.unreadable()) == 1

    def test_a_parse_error_names_the_exception(self, archive):
        doc = fixture_doc(WIN)
        doc["start_time"] = 1790777777
        doc["players"] = ["not a player"]
        _write(archive / "profile1" / "1790777777.run", doc)
        store = Store()
        store.runs()
        assert "AttributeError" in store.unreadable()["profile1/1790777777.run"]

    def test_the_list_is_rebuilt_on_every_call(self, archive):
        store = Store()
        _write(archive / "profile1" / "1790666666.run", "{")
        store.runs()
        assert store.unreadable()
        (archive / "profile1" / "1790666666.run").unlink()
        store.runs()
        assert store.unreadable() == {}


class TestSourceDirs:
    def test_extra_dirs_are_split_on_semicolons(self, tmp_path, monkeypatch):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir(), b.mkdir()
        monkeypatch.setenv("STS2_EXTRA_DIRS", f"{a};{b}")
        monkeypatch.setenv("STS2_SAVE_ROOT", str(tmp_path / "none"))
        monkeypatch.setenv("STS2_STEAM_CLOUD", "0")
        assert {p.resolve() for p in source_dirs()} == {a.resolve(), b.resolve()}

    def test_missing_dirs_are_left_out(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STS2_EXTRA_DIRS", str(tmp_path / "nope"))
        monkeypatch.setenv("STS2_SAVE_ROOT", str(tmp_path / "fixtures"))
        monkeypatch.setenv("STS2_STEAM_CLOUD", "0")
        assert all(p.exists() for p in source_dirs())

    def test_archive_dir_honours_the_environment(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STS2_ARCHIVE", str(tmp_path / "x"))
        assert archive_dir() == tmp_path / "x"
