"""Prospective fixed-filter search curves. All searches close before grading."""
import argparse
import json
import platform
import shutil
import sys
import time
from pathlib import Path

from audit_results import published_correct
from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve


def combine(left, right):
    """Visible-only fixed policy; no grade is accepted or consulted."""
    allowed = {"program", "cost", "visible_outputs", "source"}
    candidates = {}
    for item in left + right:
        if set(item) != allowed:
            raise ValueError("Mixture accepts only ungraded search candidates")
        old = candidates.get(item["program"])
        if old is None or item["cost"] < old["cost"]:
            candidates[item["program"]] = item
    return sorted(candidates.values(), key=lambda x: (x["cost"], len(x["program"]), x["program"]))[:64]


def seed_config(config, seed):
    return {"bank_seed": seed, "bank_counts": {f"seed_{seed}": config["tasks_per_seed"]},
            "visible_examples": config["visible_examples"], "hidden_examples": config["hidden_examples"],
            "max_atoms": config["max_atoms"]}


def order_for(config, banks):
    for group, tasks in banks.items():
        for index, task in enumerate(tasks):
            for budget in config["budgets"]:
                for mode in (config["modes"] if index % 2 == 0 else config["modes"][::-1]):
                    yield group, task, budget, mode


def summarize(graded):
    arms = sorted({r["arm"] for r in graded})
    metrics = {}
    for arm in arms:
        rows = [r for r in graded if r["arm"] == arm]
        metrics[arm] = {
            "tasks": len(rows), "selected_correct": sum(r["selected_correct"] for r in rows),
            "visible_fit": sum(bool(r["frontier"]) for r in rows),
            "coverage_at_k": {str(k): sum(any(f["oracle_correct"] for f in r["frontier"][:k]) for r in rows) for k in (1, 4, 16, 64)},
            "verified_programs": sum(f["oracle_correct"] for r in rows for f in r["frontier"]),
            "cost": {k: sum(r["cost"][k] for r in rows) for k in rows[0]["cost"]},
            "replay_cost": {k: sum(r["replay_cost"][k] for r in rows) for k in rows[0]["replay_cost"]},
            "by_seed": {seed: {"selected_correct": sum(r["selected_correct"] for r in rows if r["seed_group"] == seed),
                               "coverage64": sum(any(f["oracle_correct"] for f in r["frontier"]) for r in rows if r["seed_group"] == seed)}
                        for seed in sorted({r["seed_group"] for r in rows})}}
    task_map = {}
    for row in graded:
        task_map.setdefault(row["task_id"], {})[row["arm"]] = row
    contrasts = {}
    pairs = [(f"partial_empty@{b}", f"baseline@{b}") for b in (32, 64, 128, 512)]
    pairs += [("mixture@128", f"{mode}@128") for mode in ("baseline", "partial_empty")]
    for candidate, control in pairs:
        contrast = {}
        for metric in ("selected", "coverage64"):
            value = lambda r: r["selected_correct"] if metric == "selected" else any(f["oracle_correct"] for f in r["frontier"])
            wins = [key for key, rows in task_map.items() if value(rows[candidate]) and not value(rows[control])]
            losses = [key for key, rows in task_map.items() if value(rows[control]) and not value(rows[candidate])]
            contrast[metric] = {"wins": wins, "losses": losses, "delta": (len(wins) - len(losses)) / len(task_map)}
        contrasts[candidate + " minus " + control] = contrast
    a, b = metrics["partial_empty@128"], metrics["baseline@128"]
    group_wins = sum(a["by_seed"][s]["selected_correct"] > b["by_seed"][s]["selected_correct"]
                     and a["by_seed"][s]["coverage64"] > b["by_seed"][s]["coverage64"] for s in a["by_seed"])
    passed = a["selected_correct"] > b["selected_correct"] and a["coverage_at_k"]["64"] > b["coverage_at_k"]["64"] and group_wins >= 5
    return {"metrics": metrics, "contrasts": contrasts, "screen": {"passed": passed, "joint_positive_seed_groups": group_wins,
            "meaning": "Fresh-task engineering replication screen; not equal-compute superiority, kernel promotion or RSI"}}


def timed_solve(public, config, budget, macros, mode):
    details = {}
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    result = solve(public, BASE_CONFIG, budget, config["max_atoms"], macros, [], diagnostics=details, pool_mode=mode)
    timing = {"cpu_seconds": time.process_time() - start_cpu, "wall_seconds": time.perf_counter() - start_wall}
    return result, details, timing


def run(config, output):
    output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "events.jsonl")
    start = time.perf_counter()
    try:
        # Fixed protocol implementation deliberately rejects changed study grids.
        assert config["budgets"] == [32, 64, 128, 512] and config["modes"] == ["baseline", "partial_empty"]
        exclusions, origins = set(), {}
        for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
            old = json.loads(path.read_text(encoding="utf-8"))
            exclusions.update(template(t["reference"]) for tasks in old.values() for t in tasks)
            origins[str(path.relative_to(ROOT))] = file_hash(path)
        macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
        names = ["run_search_validation.py", "audit_search_validation.py", config["protocol"],
                 "rsi/common.py", "rsi/banks.py", "rsi/search.py", "rsi/search_diagnostic.py", "rsi/atom_pool_partial.py",
                 "rsi/oracle.py", "rsi/retention_run.py", "audit_results.py", "requirements.lock.txt",
                 "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
        hashes = {name: file_hash(ROOT / name) for name in names}
        for name in names:
            dest = output / "source" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, dest)
        write_json(output / "config.json", config)
        write_json(output / "common_macros.json", macros)
        write_json(output / "prior_bank_exclusions.json", {"source_hashes": origins, "templates": sorted(exclusions)})
        journal.append("preregistration", {"config": config, "config_sha256": digest(config), "source_sha256": hashes,
            "exclusions_sha256": digest(sorted(exclusions)), "macro_source_sha256": file_hash(ROOT / config["macro_source"]),
            "python": sys.version, "platform": platform.platform(), "solver_config": BASE_CONFIG})
        banks, metadata = {}, {}
        for seed in config["seeds"]:
            bank, meta = create_banks(seed_config(config, seed), exclusions)
            banks.update(bank)
            metadata.update(meta)
            exclusions.update(template(t["reference"]) for tasks in bank.values() for t in tasks)
        write_json(output / "protected_banks.json", banks)
        write_json(output / "bank_manifest.json", metadata)
        journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})
        raw = []
        for group, task, budget, mode in order_for(config, banks):
            public = public_task(task)
            result, details, timing = timed_solve(public, config, budget, macros, mode)
            replay, again, replay_timing = timed_solve(public, config, budget, macros, mode)
            assert canonical(result) == canonical(replay) and canonical(details) == canonical(again)
            request = {"task": public, "config": BASE_CONFIG, "budget": budget, "max_atoms": config["max_atoms"], "macros": macros, "mode": mode}
            row = {"seed_group": group, "task_id": task["id"], "arm": f"{mode}@{budget}",
                   "request": request, "request_sha256": digest(request), "result": result, "frontier": details["frontier"],
                   "details_sha256": digest(details), "distinct_candidates": details["distinct_candidates"],
                   "replay_result_sha256": digest(replay), "replay_details_sha256": digest(again),
                   "cost": {**result["cost"], **timing}, "replay_cost": {**replay["cost"], **replay_timing}}
            raw.append(row)
            journal.append("search", row)
            if len(raw) % 384 == 0:
                print(f"Closed {len(raw)} searches and exact replays", flush=True)
        write_json(output / "searches.json", raw)
        journal.append("search_closed", {"records": len(raw), "sha256": digest(raw)})
        by_task = {}
        for row in raw:
            by_task.setdefault(row["task_id"], {})[row["arm"]] = row
        grade_started = time.perf_counter()
        graded, grade_examples = [], 0
        for group, tasks in banks.items():
            for task in tasks:
                arms = by_task[task["id"]]
                left, right = arms["baseline@64"], arms["partial_empty@64"]
                mixture = {"task_id": task["id"], "seed_group": group, "arm": "mixture@128", "frontier": combine(left["frontier"], right["frontier"]),
                           "component_requests": [left["request_sha256"], right["request_sha256"]],
                           "cost": {k: left["cost"][k] + right["cost"][k] for k in left["cost"]},
                           "replay_cost": {k: left["replay_cost"][k] + right["replay_cost"][k] for k in left["replay_cost"]}}
                for row in list(arms.values()) + [mixture]:
                    frontier = []
                    for candidate in row["frontier"]:
                        examples = task["visible"] + task["hidden"]
                        grade = correct(candidate["program"], examples)
                        assert grade == published_correct(candidate["program"], examples)
                        frontier.append({**candidate, "oracle_correct": grade})
                        grade_examples += 2 * len(examples)
                    item = {"task_id": task["id"], "seed_group": group, "arm": row["arm"], "frontier": frontier,
                            "selected_correct": bool(frontier and frontier[0]["oracle_correct"]), "cost": row["cost"], "replay_cost": row["replay_cost"],
                            "origin_requests": row.get("component_requests", [row.get("request_sha256")])}
                    graded.append(item)
                    journal.append("grade", item)
        write_json(output / "graded.json", graded)
        result = summarize(graded)
        result.update(elapsed_seconds=time.perf_counter() - start, grading_seconds=time.perf_counter() - grade_started,
                      grade_example_upper_bound=grade_examples,
                      executed_searches=len(raw), exact_replays=len(raw),
                      execution_cost={k: sum(r["cost"][k] + r["replay_cost"][k] for r in raw) for k in raw[0]["cost"]},
                      scope="Fresh-task fixed-filter validation; no neural training or recursive improver")
        assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
        write_json(output / "results.json", result)
        journal.append("completed", {"results_sha256": digest(result)})
        seal_artifacts(output)
        print(json.dumps({"screen": result["screen"], "elapsed_seconds": result["elapsed_seconds"], "metrics": result["metrics"]}, indent=2))
    except Exception as exc:
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        write_json(output / "FAILED.json", {"type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Assertions must remain enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--config", default="configs/search-validation-v8.json")
    args = parser.parse_args()
    run(json.loads(Path(args.config).read_text()), Path(args.output))
