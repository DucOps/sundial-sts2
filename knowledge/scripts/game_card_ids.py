"""Print the card ids from Sundial's current game data, lower-cased to match knowledge/<character>/cards.yaml.

Usage: python game_card_ids.py [game-data.json] > ids.txt
       python validate_knowledge.py knowledge --card-ids ids.txt

With no argument it reads the game data the MCP server built from your install
(~/.sundial-sts2/knowledge/game/current.json, or $SUNDIAL_HOME). The list is derived from your own game files:
use it locally, don't commit it.
"""
import json
import os
import sys
from pathlib import Path


def current_game_data() -> Path:
    home = Path(os.environ.get("SUNDIAL_HOME") or Path.home() / ".sundial-sts2")
    game_dir = home / "knowledge" / "game"
    try:
        name = json.loads((game_dir / "current.json").read_text(encoding="utf-8"))["file"]
    except (OSError, ValueError, KeyError):
        sys.exit(f"No game data found in {game_dir}. Start the MCP server once (it builds it), "
                 "or pass a game-data .json file.")
    return game_dir / name


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else current_game_data()
    entries = json.loads(path.read_text(encoding="utf-8"))
    ids = sorted({e["id"].lower() for e in entries if e.get("kind") == "card" and e.get("id")})
    sys.stdout.write("\n".join(ids) + "\n")
    print(f"{len(ids)} card ids from {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
