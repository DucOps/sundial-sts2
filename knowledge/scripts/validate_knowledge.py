"""Validate Sundial knowledge files: JSON Schema + cross-file checks.

Usage: python validate_knowledge.py <knowledge_dir> [--card-ids ids.txt]
  --card-ids  optional newline-separated list of card ids from Sundial's game data;
              when given, unknown card ids are reported.
Exit code 1 on any error. Warnings (draft counts) don't fail.
Requires: pip install pyyaml jsonschema
"""
import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


def load_schema(root: Path, name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((root / "schema" / name).read_text(encoding="utf-8")))


def schema_errors(validator, data, label):
    return [f"{label}: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
            for e in validator.iter_errors(data)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--card-ids", type=Path)
    args = ap.parse_args()

    root: Path = args.root
    cards_v = load_schema(root, "cards.schema.json")
    arch_v = load_schema(root, "archetypes.schema.json")
    known_ids = None
    if args.card_ids:
        known_ids = {l.strip() for l in args.card_ids.read_text(encoding="utf-8").splitlines() if l.strip()}

    errors, warnings = [], []

    for char_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in {"schema", "scripts"}):
        cards_path = char_dir / "cards.yaml"
        arch_path = char_dir / "archetypes.yaml"
        if not cards_path.exists():
            continue
        cards_doc = yaml.safe_load(cards_path.read_text(encoding="utf-8"))
        errors += schema_errors(cards_v, cards_doc, str(cards_path))
        cards = cards_doc.get("cards", []) if isinstance(cards_doc, dict) else []

        # Duplicate ids
        seen = set()
        for c in cards:
            cid = c.get("id")
            if cid in seen:
                errors.append(f"{cards_path}: duplicate card id '{cid}'")
            seen.add(cid)
            if known_ids is not None and cid not in known_ids:
                errors.append(f"{cards_path}: unknown card id '{cid}' (not in game data)")

        drafts = sum(1 for c in cards if c.get("review", {}).get("status") == "draft")
        if drafts:
            warnings.append(f"{cards_path}: {drafts}/{len(cards)} cards still draft")

        if not arch_path.exists():
            if char_dir.name != "colorless":
                warnings.append(f"{char_dir}: no archetypes.yaml")
            continue
        arch_doc = yaml.safe_load(arch_path.read_text(encoding="utf-8"))
        errors += schema_errors(arch_v, arch_doc, str(arch_path))
        if not isinstance(arch_doc, dict):
            continue

        mechanics = {m["tag"] for m in arch_doc.get("mechanics", [])}
        by_id = {c["id"]: c for c in cards if "id" in c}

        # Unknown mechanic tags on cards
        for c in cards:
            for m in c.get("mechanics", []):
                if m.get("tag") not in mechanics:
                    errors.append(f"{cards_path}: card '{c.get('id')}' uses unknown mechanic '{m.get('tag')}'")

        for a in arch_doc.get("archetypes", []):
            aid = a.get("id")
            if a.get("mechanic") not in mechanics:
                errors.append(f"{arch_path}: archetype '{aid}' uses unknown mechanic '{a.get('mechanic')}'")
            # Keystones must exist and be payoffs of this archetype's mechanic
            for k in a.get("keystones", []):
                card = by_id.get(k)
                if card is None:
                    errors.append(f"{arch_path}: keystone '{k}' of '{aid}' has no annotation in cards.yaml")
                    continue
                roles = [m["as"] for m in card.get("mechanics", []) if m.get("tag") == a.get("mechanic")]
                if not any(r in ("payoff", "both") for r in roles):
                    errors.append(f"{arch_path}: keystone '{k}' of '{aid}' isn't a payoff of '{a.get('mechanic')}'")
            # An archetype with no possible enablers can never commit
            need_e = a.get("thresholds", {}).get("committed", {}).get("enablers", 0)
            n_e = sum(1 for c in cards for m in c.get("mechanics", [])
                      if m.get("tag") == a.get("mechanic") and m.get("as") in ("enabler", "both"))
            if need_e and n_e == 0:
                warnings.append(f"{arch_path}: archetype '{aid}' needs {need_e} enablers but no card is tagged as one")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
