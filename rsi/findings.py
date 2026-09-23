"""Versioned findings ledger for exploratory and confirmatory RSI work."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

SCHEMA_VERSION = 1


def empty_ledger() -> dict:
    return {"schema_version": SCHEMA_VERSION, "findings": []}


def load_ledger(path: Path) -> dict:
    if not path.exists():
        return empty_ledger()
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("schema_version") != SCHEMA_VERSION or not isinstance(ledger.get("findings"), list):
        raise ValueError("Unsupported findings ledger")
    return ledger


def validate_finding(finding: Mapping[str, object]) -> dict:
    required = {"id", "status", "claim", "scope", "source"}
    missing = required - set(finding)
    if missing:
        raise ValueError(f"finding missing fields: {sorted(missing)}")
    if finding["status"] not in {"observed", "planned", "null", "failed", "superseded"}:
        raise ValueError("invalid finding status")
    if finding["scope"] not in {"exploratory", "confirmatory", "engineering"}:
        raise ValueError("invalid finding scope")
    if not isinstance(finding["source"], list) or not finding["source"]:
        raise ValueError("finding source must be a non-empty list")
    return dict(finding)


def append_finding(path: Path, finding: Mapping[str, object]) -> dict:
    ledger = load_ledger(path)
    row = validate_finding(finding)
    if any(existing.get("id") == row["id"] for existing in ledger["findings"]):
        raise ValueError(f"duplicate finding id: {row['id']}")
    ledger["findings"].append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return row


def observed_findings(path: Path) -> list[dict]:
    return [row for row in load_ledger(path)["findings"] if row["status"] == "observed"]
