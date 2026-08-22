from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import yaml


REQUIRED = {"schema_version", "artifact_type", "name", "version", "license"}
ALLOWED_TYPES = {"strategy", "dataset", "knowledge", "proof", "decision"}


def load_manifest(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Le manifeste doit être un objet YAML.")
    return data


def canonical_hash(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED - data.keys())
    if missing:
        errors.append("Champs manquants : " + ", ".join(missing))
    artifact_type = data.get("artifact_type")
    if artifact_type and artifact_type not in ALLOWED_TYPES:
        errors.append(f"Type invalide : {artifact_type}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(prog="openforge")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate")
    validate_cmd.add_argument("manifest", type=Path)

    hash_cmd = sub.add_parser("hash")
    hash_cmd.add_argument("manifest", type=Path)

    args = parser.parse_args()

    try:
        data = load_manifest(args.manifest)
        if args.command == "validate":
            errors = validate(data)
            if errors:
                for error in errors:
                    print(f"ERREUR: {error}")
                return 1
            print("VALIDE")
            print(f"SHA256: {canonical_hash(data)}")
            return 0

        if args.command == "hash":
            print(canonical_hash(data))
            return 0
    except Exception as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
