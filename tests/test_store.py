"""The archive keeps every file and names the ones it can't read, instead of dropping them silently."""
import json
import shutil

from conftest import FIXTURES

from sundial_sts2.store import Store, archive_dir


def _copy_fixtures(saves):
    for f in FIXTURES.glob("*.run"):
        shutil.copy2(f, saves / f.name)


def test_sync_archives_and_loads(home):
    _, saves = home
    _copy_fixtures(saves)
    st = Store()
    assert st.sync()["added"] == 3
    assert len(st.runs()) == 3 and st.unreadable() == []


def test_a_malformed_reward_no_longer_hides_the_run(home, raw):
    _, saves = home
    _copy_fixtures(saves)
    d = raw()
    d["start_time"] = 1790300000
    for act in d["map_point_history"]:
        for pt in act:
            for c in pt["player_stats"][0].get("card_choices") or []:
                c.pop("card", None)
    (saves / "1790300000.run").write_text(json.dumps(d), encoding="utf-8")
    st = Store()
    st.sync()
    runs = st.runs()
    assert len(runs) == 4 and runs[-1].id == 1790300000
    assert st.unreadable() == []


def test_unreadable_files_are_named_and_kept(home):
    _, saves = home
    _copy_fixtures(saves)
    (saves / "1790400000.run").write_text("{not json", encoding="utf-8")
    (saves / "1790500000.run").write_text('{"hello": 1}', encoding="utf-8")
    st = Store()
    st.sync()
    assert len(st.runs()) == 3
    bad = {b["file"]: b["error"] for b in st.unreadable()}
    assert set(bad) == {"profile1/1790400000.run", "profile1/1790500000.run"}
    assert "can't read" in bad["profile1/1790400000.run"]
    assert "not a run history file" in bad["profile1/1790500000.run"]
    assert (archive_dir() / "profile1" / "1790400000.run").exists()      # never deleted from the archive


def test_a_fixed_file_is_read_again(home, raw):
    _, saves = home
    st = Store()
    archived = archive_dir() / "profile1" / "1790200000.run"
    archived.parent.mkdir(parents=True)
    archived.write_text("{broken", encoding="utf-8")
    assert st.runs() == [] and len(st.unreadable()) == 1
    archived.write_text(json.dumps(raw()), encoding="utf-8")
    import os
    os.utime(archived, (archived.stat().st_atime, archived.stat().st_mtime + 5))
    assert len(st.runs()) == 1 and st.unreadable() == []
