"""Frozen, source-only paired effect acquisition for descendant credit."""
import argparse
import datetime
import json
import platform
import shutil
import sys
import time
import traceback
from pathlib import Path

from audit_results import published_correct
from paired_credit import bank_config, branch, effects, schedule
from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.operators import apply, initial_catalog
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve


def exclusions():
    prior, templates = {}, set()
    paths = list((ROOT / "runs").glob("*/protected_banks.json"))
    paths += list((ROOT / "analysis").glob("paired-credit-fixture-*/protected_banks.json"))
    for path in sorted(paths):
        banks = json.loads(path.read_text(encoding="utf-8"))
        templates.update(template(task["reference"]) for tasks in banks.values() for task in tasks)
        prior[str(path.relative_to(ROOT)).replace("\\", "/")] = file_hash(path)
    return prior, sorted(templates)


def run(config, root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    journal = Journal(root / "events.jsonl")
    started = time.perf_counter()
    try:
        if config["pool_mode"] != "partial_empty" or config["rounds"] != 2:
            raise ValueError("Protocol requires corrected filter and two rounds")
        prior, prior_templates = exclusions()
        source_paths = list((ROOT / "rsi").glob("*.py")) + [ROOT / name for name in (
            "paired_credit.py", "run_paired_credit.py", "audit_paired_credit.py",
            config["protocol"], "requirements.lock.txt", "audit_results.py")]
        source_paths += [ROOT / "vendor/trapdoor-loom" / name for name in ("dsl.py", "parse.py", "trapdoor.py")]
        hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in source_paths}
        for path in source_paths:
            destination = root / "source" / path.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
        manifest = {"config_sha256": digest(config), "source_sha256": hashes,
                    "macro_sha256": file_hash(ROOT / config["macro_source"]),
                    "python": sys.version, "platform": platform.platform()}
        write_json(root / "config.json", config)
        write_json(root / "manifest.json", manifest)
        write_json(root / "prior_bank_exclusions.json", {"source_hashes": prior, "templates": prior_templates})
        write_json(root / "common_macros.json", macros)
        journal.append("preregistration", {"config": config, "manifest": manifest,
                       "prior_templates_sha256": digest(prior_templates)})
        banks, metadata = create_banks(bank_config(config), set(prior_templates))
        write_json(root / "protected_banks.json", banks)
        write_json(root / "bank_manifest.json", metadata)
        journal.append("banks_frozen", {"metadata": metadata, "sha256": digest(banks)})
        cache, evaluations, work = {}, {}, {"physical_searches": 0, "exact_replays": 0,
            "logical_search_requests": 0, "charged_expansions": 0, "charged_primitive_executions": 0,
            "search_wall_seconds": 0.0, "oracle_program_checks": 0,
            "oracle_string_check_upper_bound": 0}
        def evaluate(tasks, state, label, split):
            if label in evaluations:
                raise ValueError("Duplicate evaluation label")
            if split.endswith("measurement") and not closed:
                raise RuntimeError("Measurement requested before all branches closed")
            rows = []
            for task in tasks:
                request = {"task": public_task(task), "config": state,
                    "budget": config["search_budget"], "max_atoms": config["max_atoms"],
                    "macros": macros, "pool_mode": config["pool_mode"]}
                key = digest(request)
                work["logical_search_requests"] += 1
                reused = key in cache
                if not reused:
                    begin = time.perf_counter()
                    args = (request["task"], state, request["budget"], request["max_atoms"], macros, [])
                    first = solve(*args, pool_mode=request["pool_mode"])
                    replay = solve(*args, pool_mode=request["pool_mode"])
                    if canonical(first) != canonical(replay):
                        raise RuntimeError("Search replay disagrees")
                    elapsed = time.perf_counter() - begin
                    program = first["program"]
                    passed = correct(program, task["visible"] + task["hidden"])
                    if passed != published_correct(program, task["visible"] + task["hidden"]):
                        raise RuntimeError("Independent oracle disagrees with published interpreter")
                    cache[key] = {"request": request, "result": first, "oracle_correct": passed,
                                  "exact_replay_sha256": digest(replay), "search_replay_wall_seconds": elapsed}
                    work["physical_searches"] += 1
                    work["exact_replays"] += 1
                    work["search_wall_seconds"] += elapsed
                    work["charged_expansions"] += 2 * first["cost"]["expansions"]
                    work["charged_primitive_executions"] += 2 * first["cost"]["primitive_executions"]
                    work["oracle_program_checks"] += 2
                    work["oracle_string_check_upper_bound"] += 2 * (len(task["visible"]) + len(task["hidden"]))
                    journal.append("search", {"request_sha256": key, "result_sha256": digest(first),
                                   "oracle_correct": passed, "cost": first["cost"]})
                else:
                    journal.append("search_reused", {"request_sha256": key, "label": label,
                                   "source_request_sha256": key})
                rows.append({"task_id": task["id"], "request_sha256": key,
                             "oracle_correct": cache[key]["oracle_correct"], "reused": reused})
            record = {"id": label, "split": split, "task_ids": [task["id"] for task in tasks],
                      "config": dict(state), "correct": sum(row["oracle_correct"] for row in rows),
                      "n": len(rows), "rows": rows}
            evaluations[label] = record
            journal.append("evaluation", {"id": label, "sha256": digest(record),
                                          "correct": record["correct"], "split": split})
            return record
        closed = False
        catalog = {op["name"]: op for op in initial_catalog()}
        trajectories = {}
        for seed in config["source_seeds"]:
            plan = schedule(seed, config["rounds"])
            trajectories[str(seed)] = {}
            journal.append("schedule_frozen", {"seed": seed, "operator_names": plan})
            for name in [None, *catalog]:
                label = f"s{seed}_" + (name or "no_edit")
                state = apply(catalog[name], BASE_CONFIG) if name else dict(BASE_CONFIG)
                trajectory = branch(evaluate, banks, config, seed, state, label, plan)
                trajectories[str(seed)][name or "no_edit"] = trajectory
                journal.append("branch_closed", {"seed": seed, "edit": name,
                    "trajectory_sha256": digest(trajectory), "terminal_config": trajectory["terminal_config"]})
            print(f"Source group {seed}: 13 branches closed", flush=True)
        closed = True
        journal.append("optimization_closed", {"branches": sum(map(len, trajectories.values())),
                        "trajectories_sha256": digest(trajectories)})
        pairs = []
        for seed in config["source_seeds"]:
            split = f"s{seed}_measurement"
            tasks = banks[split]
            trials = trajectories[str(seed)]
            starts, ends = {}, {}
            for name, trajectory in trials.items():
                label = f"s{seed}_{name}"
                starts[name] = evaluate(tasks, trajectory["initial_config"], label + "/start", split)
                ends[name] = evaluate(tasks, trajectory["terminal_config"], label + "/end", split)
            for name in catalog:
                values = effects(starts["no_edit"]["correct"], ends["no_edit"]["correct"],
                                 starts[name]["correct"], ends[name]["correct"])
                pairs.append({"seed": seed, "edit": name, "measurement_n": len(tasks),
                    "base_start_ref": starts["no_edit"]["id"], "base_end_ref": ends["no_edit"]["id"],
                    "edited_start_ref": starts[name]["id"], "edited_end_ref": ends[name]["id"],
                    **values})
            print(f"Source group {seed}: measurement closed", flush=True)
        write_json(root / "search_records.json", cache)
        write_json(root / "evaluations.json", evaluations)
        write_json(root / "trajectories.json", trajectories)
        result = {"status": "completed", "pairs": pairs, "cost": work,
                  "elapsed_seconds": time.perf_counter() - started,
                  "headroom_observed": any(row["later_improvement"] != 0 for row in pairs),
                  "scope": "source-only paired branch probe; no inherited policy trained or tested; no RSI claim"}
        if any(file_hash(ROOT / name) != value for name, value in hashes.items()):
            raise RuntimeError("Source changed during probe")
        write_json(root / "results.json", result)
        journal.append("completed", {"results_sha256": digest(result)})
        seal_artifacts(root)
        return result
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(),
                   "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        journal.append("failed", failure)
        write_json(root / "FAILED.json", failure)
        raise


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Assertions must remain enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--config", default="configs/paired-credit-v10.json")
    args = parser.parse_args()
    print(json.dumps(run(json.loads(Path(args.config).read_text(encoding="utf-8")), Path(args.output)), indent=2))
