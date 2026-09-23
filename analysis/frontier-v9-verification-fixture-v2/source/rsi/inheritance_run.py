"""Balanced source calibration followed by table-only common-ancestor transfer."""
from __future__ import annotations

import argparse
import copy
import json
import platform
import random
import shutil
import sys
import time
import traceback
from pathlib import Path

from .banks import create_banks, template
from .common import ROOT, Journal, digest, verify_journal, write_json
from .evaluation import Evaluator, Worker, paired_bootstrap
from .evolution import evolve
from .operators import initial_catalog, shuffled_table
from .search import BASE_CONFIG
from .retention_run import file_hash, seal_artifacts
from .run import log


def run(config, root, publish_latest=True):
    journal = Journal(root / "events.jsonl")
    started = time.perf_counter()
    worker = None
    try:
        if config["proposals_per_generation"] != len(initial_catalog()):
            raise ValueError("Balanced source calibration must cover the entire initial catalog")
        if config["generations"] != 6 or config["transfer_generations"] != 6:
            raise ValueError("Protocol requires generation 0/3/6 and six transfer generations")
        for split, count in config["bank_counts"].items():
            if split != "final" and count % (len(config["seeds"]) * 6):
                raise ValueError("Each seed bank must divide into six complete slices")
        exclusions, prior = set(), {}
        for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
            banks = json.loads(path.read_text(encoding="utf-8"))
            exclusions.update(template(task["reference"]) for tasks in banks.values() for task in tasks)
            prior[str(path.relative_to(ROOT))] = file_hash(path)
        banks, metadata = create_banks(config, exclusions)
        write_json(root / "config.json", config)
        write_json(root / "protected_banks.json", banks)
        write_json(root / "bank_manifest.json", metadata)
        write_json(root / "prior_bank_exclusions.json", {"source_hashes": prior, "templates": sorted(exclusions)})
        macro_source = ROOT / config["macro_source"]
        macros = json.loads(macro_source.read_text(encoding="utf-8"))
        write_json(root / "common_macros.json", macros)
        sources = list((ROOT / "rsi").glob("*.py")) + [ROOT / config["protocol"], ROOT / "requirements.lock.txt", ROOT / "audit_inheritance.py", ROOT / "audit_results.py"]
        sources += [ROOT / "vendor/trapdoor-loom" / name for name in ("dsl.py", "parse.py", "trapdoor.py")]
        hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sources}
        for path in sources:
            dest = root / "source" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        manifest = {"schema_version": 4, "config_sha256": digest(config), "source_sha256": hashes,
                    "macro_source_sha256": file_hash(macro_source), "python": sys.version, "platform": platform.platform()}
        write_json(root / "manifest.json", manifest)
        journal.append("preregistration", {"config": config, "manifest": manifest, "bank_manifest": metadata})
        worker = Worker()
        evaluator = Evaluator(journal, config, worker)
        source_runs, trajectories, acquisition_costs = [], [], []
        seed_count = len(config["seeds"])
        def slices(prefix, index):
            result = {}
            for split in ("development", "admission"):
                tasks = banks[prefix + "_" + split]
                if len(tasks) % seed_count:
                    raise ValueError("Seed banks must divide exactly")
                width = len(tasks) // seed_count
                result[split] = tasks[index * width:(index + 1) * width]
            return result
        for index, seed in enumerate(config["seeds"]):
            log(f"Balanced source calibration: seed {seed}, all 12 edits per generation")
            before = dict(evaluator.ledger)
            source = evolve(evaluator, slices("source", index), config, seed, label="balanced_source", macros=macros)
            source_runs.append(source)
            acquisition_costs.append({"seed": seed, **{key: evaluator.ledger[key] - before[key] for key in before}})
            write_json(root / "source_trajectories.json", source_runs)
            tables = {"g0": source["snapshots"][0]["table"], "g3": source["snapshots"][3]["table"],
                      "g6": source["snapshots"][6]["table"], "scrambled_g6": shuffled_table(source["snapshots"][6]["table"], random.Random(seed + 77000)), "random": {}}
            transfer_config = {**config, "generations": config["transfer_generations"], "proposals_per_generation": config["transfer_proposals"]}
            for condition in config["conditions"]:
                log(f"Common-ancestor transfer: source {seed}, {condition}")
                before = dict(evaluator.ledger)
                trajectory = evolve(evaluator, slices("transfer", index), transfer_config, seed + 10000,
                                    initial_table=tables[condition], mode="random" if condition == "random" else "adaptive",
                                    label=f"transfer/{condition}", macros=macros)
                trajectories.append({"source_seed": seed, "condition": condition, "trajectory": trajectory,
                                     "initial_table": copy.deepcopy(tables[condition]),
                                     "compute": {key: evaluator.ledger[key] - before[key] for key in before}})
                write_json(root / "transfer_trajectories.json", trajectories)
                journal.append("transfer_closed", {"source_seed": seed, "condition": condition,
                                                    "config_sha256": digest(trajectory["config"]), "initial_table_sha256": digest(tables[condition])})
        journal.append("optimization_closed", {"source_runs": len(source_runs), "transfer_runs": len(trajectories)})
        log("All optimization closed; evaluating common ancestor and final descendants")
        ancestor = evaluator.evaluate(banks["final"], BASE_CONFIG, "final/ancestor", macros=macros)
        measurements = []
        for item in trajectories:
            score = evaluator.evaluate(banks["final"], item["trajectory"]["config"], f"final/{item['condition']}/{item['source_seed']}", macros=macros)
            measurements.append({"source_seed": item["source_seed"], "condition": item["condition"], "accuracy": score["accuracy"],
                                 "correct": score["correct"], "n": score["n"], "gain_over_ancestor": score["accuracy"] - ancestor["accuracy"],
                                 "task_scores": [int(r["oracle_correct"]) for r in score["results"]],
                                 "config": item["trajectory"]["config"], "request_sha256": score["request_sha256"],
                                 "accepted_edits": sum(r["accepted"] for r in item["trajectory"]["decisions"])})
        contrasts = {}
        for control in ("g0", "g3", "scrambled_g6", "random"):
            pairs = []
            for seed in config["seeds"]:
                left = next(r for r in measurements if r["source_seed"] == seed and r["condition"] == "g6")
                right = next(r for r in measurements if r["source_seed"] == seed and r["condition"] == control)
                pairs.append({"source_seed": seed, **paired_bootstrap(left["task_scores"], right["task_scores"])})
            contrasts["g6_minus_" + control] = {"mean": sum(p["mean"] for p in pairs) / len(pairs), "paired_sources": pairs}
        evaluator.assert_integrity()
        if any(file_hash(ROOT / name) != expected for name, expected in hashes.items()):
            raise RuntimeError("Source changed during experiment")
        result = {"run_id": root.name, "status": "completed", "ancestor": ancestor, "measurements": measurements,
                  "contrasts": contrasts, "source_acquisition_compute": acquisition_costs, "ledger": evaluator.ledger,
                  "wall_seconds": time.perf_counter() - started,
                  "compute_conventions": {"search_expansions": "Logical expansions charged for original and replay searches",
                                          "primitive_executions": "Logical atom-pool executions including replay; cached work may not execute again",
                                          "oracle_string_executions": "Charged example-count upper bound; interpreter short circuits can perform fewer executions",
                                          "ledger_wall_seconds": "Measured worker request/replay time; excludes host grading and journaling",
                                          "wall_seconds": "Measured whole-run time through result construction; excludes audit"},
                  "limitations": [f"{len(config['seeds'])} source seeds", "shared final tasks", "bounded numeric edit space", "transfer opportunities matched, total acquisition compute not matched", "no neural experiment"]}
        write_json(root / "results.json", result)
        lines = ["# Balanced calibration and table inheritance", "", "Component test; does not establish RSI.", "",
                 f"Common ancestor: {ancestor['correct']}/{ancestor['n']} = {ancestor['accuracy']:.2%}", "",
                 "| Source seed | Table | Correct | Accuracy | Gain over ancestor | Accepted edits |", "| --- | --- | --- | --- | --- | --- |"]
        for r in measurements:
            lines.append(f"| {r['source_seed']} | {r['condition']} | {r['correct']}/{r['n']} | {r['accuracy']:.2%} | {r['gain_over_ancestor']:+.2%} | {r['accepted_edits']} |")
        lines += ["", "## Primary contrasts", ""]
        for name, contrast in contrasts.items():
            lines.append(f"- {name}: {contrast['mean']:+.2%}; individual source differences: " + ", ".join(f"{p['mean']:+.2%}" for p in contrast["paired_sources"]))
        lines += ["", "See results.json for paired-task descriptive intervals, all cost ledgers, and limits. A small source sample and a shared final bank do not establish broad generalization. Acquisition costs remain separate from equal downstream edit opportunities."]
        (root / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        journal.append("completed", {"results_sha256": digest(result)})
        verify_journal(journal.path)
        seal_artifacts(root)
        if publish_latest:
            write_json(ROOT / "runs/latest-inheritance.json", {"run_id": root.name, "report": str(root / "REPORT.md")})
        log(f"Completed: {root / 'REPORT.md'}")
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        journal.append("failed", failure)
        write_json(root / "FAILED.json", failure)
        raise
    finally:
        if worker:
            worker.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/inheritance-v4.json")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    root = ROOT / "runs" / args.run_id
    root.mkdir(parents=True, exist_ok=False)
    run(config, root)


if __name__ == "__main__":
    main()
