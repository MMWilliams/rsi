"""Independent full candidate and oracle replay for encoded transfer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.retention_run import file_hash
from run_cross_family_macro_v75 import create_cross_family_banks
from run_encoding_transfer import ARMS, candidates, measure


def audit(output):
    output = Path(output)
    read = lambda name: json.loads((output / name).read_text(encoding="utf-8"))
    assert not (output / "FAILED.json").exists()
    sealed = read("artifact_manifest.json")
    present = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
    assert present - {"artifact_manifest.json", "audit.json"} == set(sealed)
    for name, row in sealed.items():
        assert file_hash(output / name) == row["sha256"] and (output / name).stat().st_size == row["bytes"]
    for name, sha in read("source_manifest.json").items():
        assert file_hash(output / "source" / name) == sha
    cfg = read("config.json")
    source = ROOT / cfg["source_run"] / "generic_lineage_library.json"
    assert file_hash(source) == read("results.json")["library_sha256"]
    library = read("source_library.json")
    assert digest(library) == digest(json.loads(source.read_text(encoding="utf-8")))
    banks, metadata = create_cross_family_banks(cfg)
    assert digest(banks) == digest(read("protected_banks.json"))
    assert digest(metadata) == digest(read("bank_manifest.json"))
    pools = read("candidate_pools.json")
    result = read("results.json")
    checked = 0
    for arm in ARMS:
        expected = []
        for task in banks["final"]:
            public = {"id": task["id"], "visible": task["visible"]}
            rows = candidates(public, library, cfg, arm)
            assert digest(rows) == digest(pools[task["id"]][arm]), (task["id"], arm)
            expected.append(measure(task, rows))
            checked += 1
        saved = result["summary"][arm]
        assert digest(expected) == digest(saved["rows"])
        assert saved["correct"] == sum(row["correct"] for row in expected)
        assert saved["reachable"] == sum(row["reachable"] for row in expected)
        assert saved["candidates"] == sum(row["candidate_count"] for row in expected)
    if cfg.get("combine_policy"):
        assert cfg["combine_policy"] == "direct_if_available_else_adaptive"
        expected = []
        for task in banks["final"]:
            task_pools = pools[task["id"]]
            source = "direct_grammar" if task_pools["direct_grammar"] else "adaptive_lineage"
            expected.append({**measure(task, task_pools[source]), "source": source})
        saved = result["summary"]["combined"]
        assert digest(expected) == digest(saved["rows"])
        assert saved["correct"] == sum(row["correct"] for row in expected)
        assert saved["reachable"] == sum(row["reachable"] for row in expected)
    events = [json.loads(line) for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(output / "events.jsonl") == len(events)
    assert events[-1]["kind"] == "completed" and events[-1]["payload"]["sha256"] == digest(result)
    report = {"status": "passed", "artifacts_hashed": len(sealed), "candidate_generations_replayed": checked,
              "tasks": len(banks["final"]), "scope": "fixed catalog; fresh encoding transfer"}
    write_json(output / "audit.json", report)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    args = ap.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
