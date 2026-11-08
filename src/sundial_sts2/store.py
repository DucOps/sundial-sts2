"""Find run history on disk, keep a permanent archive of it, and load it.

The game keeps only your most recent runs in `saves/history`, so every time the
server starts (and before each tool call) new `.run` files are copied into an
archive that is never pruned. All analysis reads from the archive.

Configuration (environment variables):
  STS2_SAVE_ROOT   Game save folder. Default: %APPDATA%\\SlayTheSpire2 on Windows,
                   ~/Library/Application Support/SlayTheSpire2 on macOS,
                   ~/.local/share/SlayTheSpire2 on Linux.
  STS2_STEAM_CLOUD Also scan Steam Cloud's local copy (Steam/userdata/<id>/2868840/remote). Default 1; 0 turns it off.
  STS2_EXTRA_DIRS  More folders to scan, separated by ';' (e.g. an unzipped phone export).
  STS2_ARCHIVE     Archive folder. Default: ~/.sundial-sts2/archive
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

from .parse import Run, looks_like_run, parse_run


def default_save_root() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "SlayTheSpire2"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "SlayTheSpire2"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "SlayTheSpire2"


LEGACY_HOME = Path.home() / ".spire-ledger"   # the prototype's data folder (before the rename to Sundial)
_migrated = False


def data_home() -> Path:
    home = Path(os.environ.get("SUNDIAL_HOME", Path.home() / ".sundial-sts2"))
    _migrate_legacy(home)
    return home


def _migrate_legacy(home: Path) -> None:
    """One-time copy of ~/.spire-ledger (archive, experts, analyses, lessons, knowledge) into the new folder.
    The old folder is left in place; delete it yourself once you're happy."""
    global _migrated
    if _migrated:
        return
    _migrated = True
    if "SUNDIAL_HOME" in os.environ or home.exists() or not LEGACY_HOME.is_dir():
        return
    shutil.copytree(LEGACY_HOME, home)
    print(f"sundial-sts2: copied {LEGACY_HOME} to {home} (one-time migration)", file=sys.stderr)


def archive_dir() -> Path:
    return Path(os.environ.get("STS2_ARCHIVE", data_home() / "archive"))


STEAM_APP_ID = "2868840"   # Slay the Spire 2


def steam_cloud_dirs() -> list[Path]:
    """Steam Cloud's local copies of the save folder (Steam/userdata/<id>/2868840/remote).
    Runs played on another device (e.g. a Steam Deck) sync here even before the game is launched on this
    machine, so they can be newer than the game's own save folder."""
    steams: list[Path] = []
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                steams.append(Path(winreg.QueryValueEx(k, "SteamPath")[0]))
        except OSError:
            pass
        steams.append(Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam")
    elif sys.platform == "darwin":
        steams.append(Path.home() / "Library" / "Application Support" / "Steam")
    else:
        steams += [Path.home() / ".steam" / "steam", Path.home() / ".local" / "share" / "Steam"]
    out: list[Path] = []
    for s in steams:
        for d in sorted((s / "userdata").glob(f"*/{STEAM_APP_ID}/remote")) if (s / "userdata").is_dir() else []:
            if d.resolve() not in [o.resolve() for o in out]:
                out.append(d)
    return out


def source_dirs() -> list[Path]:
    roots = [Path(os.environ.get("STS2_SAVE_ROOT", default_save_root()))]
    if os.environ.get("STS2_STEAM_CLOUD", "1") != "0":
        roots += steam_cloud_dirs()
    roots += [Path(p) for p in os.environ.get("STS2_EXTRA_DIRS", "").split(";") if p.strip()]
    return [r for r in roots if r.exists()]


_PROFILE = re.compile(r"(profile\d+)", re.I)


def _profile_of(path: Path) -> str:
    m = _PROFILE.search(path.as_posix())
    return m.group(1).lower() if m else "profile1"


class Store:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Run | None]] = {}
        self.last_sync: dict = {}

    def sync(self) -> dict:
        """Copy any new or changed .run files from the sources into the archive."""
        arch = archive_dir()
        added = updated = 0
        scanned = 0
        for root in source_dirs():
            for f in root.rglob("*.run"):
                if "history" not in f.parent.name:
                    continue
                scanned += 1
                dest = arch / _profile_of(f) / f.name
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
                    added += 1
                elif f.stat().st_mtime > dest.stat().st_mtime + 1:
                    shutil.copy2(f, dest)
                    updated += 1
        self.last_sync = {"sources": [str(p) for p in source_dirs()], "archive": str(arch),
                          "scanned": scanned, "added": added, "updated": updated}
        return self.last_sync

    def runs(self) -> list[Run]:
        """All archived runs, oldest first. Parsed files are cached by mtime."""
        out: list[Run] = []
        arch = archive_dir()
        if not arch.exists():
            return out
        for f in arch.rglob("*.run"):
            k, m = str(f), f.stat().st_mtime
            hit = self._cache.get(k)
            if not hit or hit[0] != m:
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                    run = parse_run(d, profile=_profile_of(f), file=f.name) if looks_like_run(d) else None
                except (OSError, ValueError, KeyError, TypeError):
                    run = None
                hit = (m, run)
                self._cache[k] = hit
            if hit[1]:
                out.append(hit[1])
        out.sort(key=lambda r: (r.start, r.profile))
        return out
