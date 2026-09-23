"""Common-ancestor transfer of a learned fragment proposer, protocol v7."""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import time
from pathlib import Path

from .banks import create_banks, template
from .common import ROOT, Journal, digest, verify_journal, write_json
from .evaluation import Evaluator, Worker, paired_bootstrap
from .library import evolve_library, scramble_memory
from .retention_run import file_hash, seal_artifacts
from .search import BASE_CONFIG


def run(config, root):
    journal = Journal(root / "events.jsonl")
    started, worker = time.perf_counter(), None
    try:
        assert config["generations"] == 6
        assert config["conditions"] == ["g0", "g3", "g6", "scrambled_g6", "numeric_pair", "frozen_library"]
        for name, count in config["bank_counts"].items():
            assert name == "final" or count % (len(config["seeds"]) * 6) == 0
        exclusions, prior = set(), {}
        for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
            old = json.loads(path.read_text(encoding="utf-8"))
            exclusions.update(template(t["reference"]) for tasks in old.values() for t in tasks)
            prior[str(path.relative_to(ROOT))] = file_hash(path)
        banks, metadata = create_banks(config, exclusions)
        macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
        for name, data in (("config.json", config), ("protected_banks.json", banks), ("bank_manifest.json", metadata),
                           ("prior_bank_exclusions.json", {"source_hashes": prior, "templates": sorted(exclusions)}), ("common_macros.json", macros)):
            write_json(root / name, data)
        paths = list((ROOT / "rsi").glob("*.py")) + [ROOT / p for p in (config["protocol"], "requirements.lock.txt", "audit_library.py", "audit_inheritance.py", "audit_results.py")]
        paths += [ROOT / "vendor/trapdoor-loom" / p for p in ("dsl.py", "parse.py", "trapdoor.py")]
        hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}
        for path in paths:
            dest = root / "source" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        manifest = {"config_sha256": digest(config), "source_sha256": hashes,
                    "macro_source_sha256": file_hash(ROOT / config["macro_source"]), "python": sys.version, "platform": platform.platform()}
        write_json(root / "manifest.json", manifest)
        journal.append("preregistration", {"config": config, "manifest": manifest, "bank_manifest": metadata})
        worker = Worker()
        evaluator = Evaluator(journal, config, worker)
        trajectories, acquisitions, scramble_records = [], [], []

        def sliced(prefix, index):
            result = {}
            for name in ("harvest", "development", "admission"):
                tasks = banks[f"{prefix}_{name}"]
                width = len(tasks) // len(config["seeds"])
                result[name] = tasks[index * width:(index + 1) * width]
            return result

        def trajectory(prefix, index, seed, condition, initial):
            label = f"{prefix}/{condition}/{seed}"
            before = dict(evaluator.ledger)
            print(f"Optimizing {label}", flush=True)
            mode = condition if condition in ("numeric_pair", "frozen_library") else "library"
            result = evolve_library(evaluator, sliced(prefix, index), config, label, initial, macros, mode)
            entry = {"phase": prefix, "seed": seed, "condition": condition, "trajectory": result,
                     "compute": {k: evaluator.ledger[k] - before[k] for k in before}}
            trajectories.append(entry)
            write_json(root / "trajectories.json", trajectories)
            journal.append("trajectory_closed", {"label": label, "snapshot_sha256": digest(result["snapshots"][6])})
            return entry

        for index, seed in enumerate(config["seeds"]):
            source = trajectory("source", index, seed, "library", {})
            acquisitions.append({"seed": seed, "compute": source["compute"],
                                 "ranking_primitive_upper_bound": source["trajectory"]["ranking_primitive_upper_bound"]})
            snapshots = source["trajectory"]["snapshots"]
            scrambled, trace = scramble_memory(snapshots[6]["memory"], seed + 77007)
            scramble_records.append({"seed": seed, "memory": scrambled, "trace": trace})
            journal.append("memory_scrambled", {"seed": seed, "memory_sha256": digest(scrambled), "trace": trace})
            write_json(root / "scrambled_memories.json", scramble_records)
            initial = {"g0": {}, "g3": snapshots[3]["memory"], "g6": snapshots[6]["memory"],
                       "scrambled_g6": scrambled, "numeric_pair": {}, "frozen_library": {}}
            for condition in config["conditions"]:
                trajectory("transfer", index, seed, condition, initial[condition])
        journal.append("optimization_closed", {"trajectories": len(trajectories)})
        print("Optimization closed; scoring ancestor and generation-3/6 snapshots", flush=True)
        ancestor = evaluator.evaluate(banks["final"], BASE_CONFIG, "final/ancestor", macros=macros)
        measurements = []
        for entry in trajectories:
            for generation in (3, 6):
                state = entry["trajectory"]["snapshots"][generation]
                label = f"final/{entry['trajectory']['label']}/g{generation}"
                score = evaluator.evaluate(banks["final"], state["config"], label, macros=state["macros"])
                measurements.append({"phase": entry["phase"], "source_seed": entry["seed"], "condition": entry["condition"],
                                     "generation": generation, "label": label, "accuracy": score["accuracy"],
                                     "correct": score["correct"], "n": score["n"], "task_scores": [int(r["oracle_correct"]) for r in score["results"]],
                                     "request_sha256": score["request_sha256"]})
        final = {(m["source_seed"], m["condition"]): m for m in measurements if m["phase"] == "transfer" and m["generation"] == 6}
        contrasts = {}
        for condition in config["conditions"]:
            if condition == "g6":
                continue
            pairs = [{"source_seed": seed, **paired_bootstrap(final[seed, "g6"]["task_scores"], final[seed, condition]["task_scores"])} for seed in config["seeds"]]
            contrasts["g6_minus_" + condition] = {"mean": sum(p["mean"] for p in pairs) / len(pairs), "paired_sources": pairs}
        wins = sum(final[s, "g6"]["correct"] > final[s, "g0"]["correct"] and final[s, "g6"]["correct"] > final[s, "scrambled_g6"]["correct"] for s in config["seeds"])
        screen = {"all_mean_contrasts_positive": all(c["mean"] > 0 for c in contrasts.values()), "joint_source_wins": wins,
                  "required_source_wins": len(config["seeds"]) // 2 + 1}
        screen["passed"] = screen["all_mean_contrasts_positive"] and wins >= screen["required_source_wins"]
        assert all(file_hash(ROOT / name) == value for name, value in hashes.items()), "Source changed during study"
        evaluator.assert_integrity()
        result = {"run_id": root.name, "ancestor": ancestor, "measurements": measurements, "contrasts": contrasts,
                  "screen": screen, "source_acquisition": acquisitions, "ledger": evaluator.ledger,
                  "ranking_primitive_upper_bound": sum(t["trajectory"]["ranking_primitive_upper_bound"] for t in trajectories),
                  "wall_seconds": time.perf_counter() - started,
                  "cost_note": "Source executed once; charge its full ledger to each corresponding transfer arm, including controls. Matched opportunities/ceilings, not actual primitive operations or FLOPs. Prior common-library acquisition shared and archived in v2."}
        write_json(root / "results.json", result)
        journal.append("completed", {"results_sha256": digest(result), "screen": screen})
        verify_journal(journal.path)
        seal_artifacts(root)
        print(json.dumps({"screen": screen, "contrasts": {k: v["mean"] for k, v in contrasts.items()}, "wall_seconds": result["wall_seconds"]}, indent=2), flush=True)
        return result
    except Exception as exc:
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        write_json(root / "FAILED.json", {"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        if worker:
            worker.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/library-v7.json")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = ROOT / "runs" / args.run_id
    root.mkdir(parents=True, exist_ok=False)
    run(json.loads((ROOT / args.config).read_text(encoding="utf-8")), root)
