"""Run the frozen v6 offline source-only diagnostic, retaining every artifact."""
import argparse
import json
import platform
import shutil
import time
from pathlib import Path

import numpy as np

from rsi.common import Journal, ROOT, write_json
from rsi.contextual import evaluate_models, extract, sha, summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--sources", nargs="+", default=["runs/inheritance-20260916-v4", "runs/inheritance-20260916-v5"])
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    files = ["run_context_diagnostic.py", "audit_context_diagnostic.py", "rsi/contextual.py", "rsi/common.py",
             "rsi/search.py", "rsi/operators.py", "EXPERIMENT-v6-context-diagnostic.md", "requirements.lock.txt"]
    for name in files:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    source_hashes = {name: sha(ROOT / name) for name in files}
    journal.append("started", {"source_paths": args.sources, "source_hashes": source_hashes,
                               "python": platform.python_version(), "numpy": np.__version__})
    try:
        dataset = extract([ROOT / p for p in args.sources])
        assert len(dataset["rows"]) == 864 and len({r["group"] for r in dataset["rows"]}) == 9
        write_json(output / "dataset.json", dataset)
        journal.append("dataset_extracted", {"contexts": len(dataset["rows"]), "dataset_sha256": sha(output / "dataset.json")})
        analysis = evaluate_models(dataset, lambda group: journal.append("fold_completed", {"held_out_source": group}))
        write_json(output / "analysis.json", analysis)
        results = summarize(dataset, analysis)
        results["elapsed_seconds"] = time.perf_counter() - started
        results["scope"] = "Exploratory offline source-only prediction and ranking; no new search, neural training or RSI claim"
        write_json(output / "results.json", results)
        assert all(sha(ROOT / name) == value for name, value in source_hashes.items()), "Source changed during diagnostic"
        journal.append("completed", {"screen": results["screen"], "elapsed_seconds": results["elapsed_seconds"]})
        manifest = {p.relative_to(output).as_posix(): {"sha256": sha(p), "bytes": p.stat().st_size}
                    for p in output.rglob("*") if p.is_file()}
        write_json(output / "artifact_manifest.json", manifest)
        print(json.dumps({k: results[k] for k in ("contexts", "task_edit_observations", "nonzero_labels", "overall", "screen", "elapsed_seconds")}, indent=2))
    except Exception as exc:
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        write_json(output / "FAILED.json", {"type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    main()
