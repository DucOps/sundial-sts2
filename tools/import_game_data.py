"""Build Sundial's game knowledge from your own Slay the Spire 2 install, by hand.

The MCP server does this by itself (on first start and after each game patch), so you only need this to force a
rebuild or to point at a game folder it can't find:

    uv run python tools/import_game_data.py ["C:\\...\\steamapps\\common\\Slay the Spire 2"]

See src/sundial_sts2/gamedata.py for what it reads and the caveats (derived from your own game files, for your own
use; game updates may break it; future support isn't guaranteed).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sundial_sts2.gamedata import main  # noqa: E402

if __name__ == "__main__":
    main()
