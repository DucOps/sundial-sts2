"""Convert the community card/relic/potion lists from https://github.com/cjodo/sts2
(cards.json, relics.json, potions.json) into Sundial knowledge files.

The data is scraped from a third-party site, has no licence, and dates from early
access v0.98. It is NOT shipped with this project. Run this yourself for personal use:

    git clone https://github.com/cjodo/sts2 %TEMP%\\sts2-data
    python tools/import_community_data.py %TEMP%\\sts2-data

Output: ~/.sundial-sts2/knowledge/community.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    text = re.sub(r"\s+([.,])", r"\1", text)
    # the scraper sometimes captured the description twice
    half = len(text) // 2
    for cut in range(half - 2, half + 3):
        a, b = text[:cut].strip(), text[cut:].strip()
        if a and a == b:
            text = a
            break
    # energy/star icons were images on the source site, so their amounts are lost
    text = re.sub(r"\b(Gain|gain|gains|Gains)\s*\.", r"\1 [icon amount missing].", text)
    return text


def to_id(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")


def main(src: str) -> None:
    src_p = Path(src)
    out: list[dict] = []
    for c in json.loads((src_p / "cards.json").read_text(encoding="utf-8")):
        out.append({"id": to_id(c["Title"]), "kind": "card", "name": c["Title"], "text": clean(c.get("Description", "")),
                    "character": c.get("Character", ""), "type": c.get("Type", ""), "cost": c.get("EnergyCost", ""),
                    "rarity": c.get("Rarity", ""), "source": "community (cjodo/sts2)", "as_of": "v0.98"})
    for kind, file in (("relic", "relics.json"), ("potion", "potions.json")):
        for c in json.loads((src_p / file).read_text(encoding="utf-8")):
            out.append({"id": to_id(c["Name"]), "kind": kind, "name": c["Name"], "text": clean(c.get("Description", "")),
                        "character": c.get("Character", ""), "rarity": c.get("Rarity", ""),
                        "source": "community (cjodo/sts2)", "as_of": "v0.98"})
    dest = Path(os.environ.get("SUNDIAL_HOME", Path.home() / ".sundial-sts2")) / "knowledge"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "community.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(out)} entries to {dest / 'community.json'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
