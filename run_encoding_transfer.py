"""Fresh-bank replay of V86's retained representation hypotheses."""
from __future__ import annotations

import argparse
import json
import shutil
import time
import traceback
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.generic_body_evolution import synthesize_library_body_predicates, synthesize_encoding_adaptive_library_predicates
from rsi.retention_run import file_hash, seal_artifacts
from rsi.self_editing_grammar import SAFE_OPS, synthesize_self_edit_predicates
from rsi.semantic_invention import evaluate_program
from run_ast_v66 import _direct_ast_candidates
from run_cross_family_macro_v75 import create_cross_family_banks


ARMS = ("identity_lineage", "adaptive_lineage", "direct_grammar")


def candidates(public, library, cfg, arm):
    visible = public["visible"]
    if arm == "identity_lineage":
        predicates = synthesize_library_body_predicates(visible, library, encodings=("identity",))
    elif arm == "adaptive_lineage":
        predicates = synthesize_encoding_adaptive_library_predicates(visible, library, cfg["adaptive_encodings"])
    elif arm == "direct_grammar":
        predicates = synthesize_self_edit_predicates(visible, SAFE_OPS)
    else:
        raise ValueError(arm)
    return _direct_ast_candidates(public, predicates)


def measure(task, rows):
    correct = [bool(evaluate_program(row["program"], task["visible"] + task["hidden"])) for row in rows]
    selected = min(range(len(rows)), key=lambda i: (len(rows[i]["program"]), rows[i]["program"])) if rows else None
    return {"task_id": task["id"], "program": rows[selected]["program"] if selected is not None else "",
            "correct": correct[selected] if selected is not None else False,
            "reachable": any(correct), "candidate_count": len(rows), "candidate_correct": correct}


def run(cfg, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "events.jsonl")
    started = time.perf_counter()
    try:
        paths = sorted((ROOT / "rsi").glob("*.py")) + [ROOT / name for name in
            ("run_ast_v66.py", "run_cross_family_macro_v75.py", "run_encoding_transfer.py",
             "audit_encoding_transfer.py", cfg["protocol"])]
        hashes = {path.relative_to(ROOT).as_posix(): file_hash(path) for path in paths}
        for path in paths:
            dest = output / "source" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        source = ROOT / cfg["source_run"] / "generic_lineage_library.json"
        source_hash = file_hash(source)
        library = json.loads(source.read_text(encoding="utf-8"))
        write_json(output / "source_library.json", library)
        write_json(output / "config.json", cfg)
        write_json(output / "source_manifest.json", hashes)
        journal.append("preregistration", {"config": cfg, "source_sha256": hashes, "library_sha256": source_hash})
        banks, metadata = create_cross_family_banks(cfg)
        write_json(output / "protected_banks.json", banks)
        write_json(output / "bank_manifest.json", metadata)
        journal.append("bank_frozen", {"sha256": digest(banks)})
        pools = {}
        results = {arm: [] for arm in ARMS}
        costs = {arm: 0.0 for arm in ARMS}
        for task in banks["final"]:
            public = {"id": task["id"], "visible": task["visible"]}
            pools[task["id"]] = {}
            for arm in ARMS:
                begin = time.perf_counter()
                rows = candidates(public, library, cfg, arm)
                costs[arm] += time.perf_counter() - begin
                pools[task["id"]][arm] = rows
                results[arm].append(measure(task, rows))
        if cfg.get("combine_policy"):
            if cfg["combine_policy"] != "direct_if_available_else_adaptive":
                raise ValueError(cfg["combine_policy"])
            results["combined"] = []
            for task in banks["final"]:
                task_pools = pools[task["id"]]
                source = "direct_grammar" if task_pools["direct_grammar"] else "adaptive_lineage"
                results["combined"].append({**measure(task, task_pools[source]), "source": source})
        write_json(output / "candidate_pools.json", pools)
        summary = {arm: {"correct": sum(row["correct"] for row in rows),
                         "reachable": sum(row["reachable"] for row in rows),
                         "n": len(rows), "candidates": sum(row["candidate_count"] for row in rows),
                         "seconds": (costs["direct_grammar"] + costs["adaptive_lineage"] if arm == "combined" else costs[arm]),
                         "rows": rows} for arm, rows in results.items()}
        result = {"status": "completed", "summary": summary, "library_sha256": source_hash,
                  "elapsed_seconds": time.perf_counter() - started,
                  "scope": "fresh encoded stack-transition bank; fixed encoding catalog"}
        write_json(output / "results.json", result)
        if any(file_hash(ROOT / name) != sha for name, sha in hashes.items()):
            raise RuntimeError("source changed during run")
        journal.append("completed", {"sha256": digest(result)})
        seal_artifacts(output)
        return {"status": "completed", "output": str(output),
                "scores": {arm: {key: value for key, value in row.items() if key in ("correct", "reachable", "n", "candidates")}
                           for arm, row in summary.items()}}
    except BaseException as exc:
        write_json(output / "FAILED.json", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--config", default="configs/encoding-transfer-2026-09-17.json")
    args = ap.parse_args()
    print(json.dumps(run(json.loads((ROOT / args.config).read_text(encoding="utf-8")), ROOT / args.output), indent=2))
