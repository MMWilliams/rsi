"""Refresh the GPU verification fixture after an intentional source-contract update."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.common import canonical, digest, write_json
from rsi.retention_run import file_hash, seal_artifacts


FIXTURE = ROOT / "analysis" / "frontier-v9-verification-fixture-v2"


def main():
    changed_sources = ["rsi/oracle.py", "audit_retention.py", "audit_frontier_distillation.py",
                       "rsi/operators.py", "rsi/evolution.py"]
    for relative in changed_sources:
        target = FIXTURE / "source" / relative
        target.write_bytes((ROOT / relative).read_bytes())
    manifest_path = FIXTURE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative in changed_sources:
        manifest["source_sha256"][relative] = file_hash(FIXTURE / "source" / relative)
    write_json(manifest_path, manifest)
    events_path = FIXTURE / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events[0]["payload"]["manifest"] = manifest
    previous = "0" * 64
    for index, event in enumerate(events):
        event.pop("sha256", None)
        event["seq"] = index
        event["previous"] = previous
        event["sha256"] = digest(event)
        previous = event["sha256"]
    events_path.write_text("\n".join(canonical(event) for event in events) + "\n", encoding="utf-8")
    seal_artifacts(FIXTURE)
    print(file_hash(target))


if __name__ == "__main__":
    main()
