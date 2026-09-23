"""Predeclared semantic policy transfer pilot; V86 remains a distinct lane."""
from __future__ import annotations

import argparse
import json
import random
import shutil
import time
import traceback
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import evaluate_program
from stitch_ten import mixed_banks, source_candidates


ARMS = ("v67", "v70", "v72", "v73")
SETS = {
    "v67": ("v67",), "v73": ("v73",),
    "v67_v73": ("v67", "v73"),
    "representation": ("v70", "v72"),
    "top4_semantic": ARMS,
}
FROZEN = (100, 10, 5, 2, 1, 0, -1, 0, 0, 0, 0)
NAMES = ("div", "mul", "xor", "mask", "shr", "not")


def features(row):
    program = row["program"]
    return tuple(program.count(name) for name in NAMES) + (len(program),) + tuple(int(row["source"] == arm) for arm in ARMS)


def select(rows, allowed, weights):
    choices = [row for row in rows if row["source"] in allowed]
    return max(choices, key=lambda row: (sum(a*b for a, b in zip(weights, features(row))),
                                          -len(row["program"]), row["program"], row["source"])) if choices else None


def score(tasks, pools, allowed, weights):
    rows = []
    for task in tasks:
        choices = [row for row in pools[task["id"]] if row["source"] in allowed]
        picked = select(choices, allowed, weights)
        correct = picked["oracle_correct"] if picked else False
        reach = any(row["oracle_correct"] for row in choices)
        rows.append({"task_id": task["id"], "family": task["family"],
                     "source": picked["source"] if picked else "none", "program": picked["program"] if picked else "",
                     "correct": bool(correct), "reachable": bool(reach), "candidate_count": len(choices)})
    return {"correct": sum(r["correct"] for r in rows), "reachable": sum(r["reachable"] for r in rows),
            "n": len(rows), "rows": rows}


def evolve(tasks, pools, allowed, cfg, seed):
    rng = random.Random(seed)
    population = [FROZEN]
    while len(population) < cfg["population_size"]:
        population.append(tuple(rng.randint(-20, 120) for _ in range(6)) +
                          (rng.randint(-3, 0),) + tuple(rng.randint(-40, 40) for _ in ARMS))
    trace = []
    for generation in range(cfg["generations"] + 1):
        evaluated = [(score(tasks, pools, allowed, weights)["correct"], weights) for weights in population]
        evaluated.sort(key=lambda item: (item[0], item[1]), reverse=True)
        trace.append({"generation": generation, "best_correct": evaluated[0][0], "best_weights": evaluated[0][1]})
        if generation == cfg["generations"]:
            return evaluated[0][1], trace
        elites = [weights for _correct, weights in evaluated[:cfg["elite_count"]]]
        next_population = list(elites)
        while len(next_population) < cfg["population_size"]:
            left, right = rng.choice(elites), rng.choice(elites)
            child = [left[i] if rng.random() < 0.5 else right[i] for i in range(len(FROZEN))]
            index = rng.randrange(len(child))
            child[index] += rng.randint(-15, 15)
            next_population.append(tuple(child))
        population = next_population


def banks_for(cfg):
    source_cfg = dict(cfg, bank_seed=cfg["source_seed"])
    banks = mixed_banks(source_cfg)
    for seed in cfg["transfer_seeds"]:
        transfer_cfg = dict(cfg, bank_seed=seed, bank_counts={"transfer": cfg["transfer_count"]})
        banks[f"transfer_{seed}"] = mixed_banks(transfer_cfg)["transfer"]
    return banks


def run(cfg, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "events.jsonl")
    started = time.perf_counter()
    try:
        paths = sorted((ROOT / "rsi").glob("*.py")) + [ROOT / name for name in
            ("stitch_ten.py", "run_policy_transfer.py", "audit_policy_transfer.py", "run_ast_v66.py", cfg["protocol"])]
        hashes = {path.relative_to(ROOT).as_posix(): file_hash(path) for path in paths}
        for path in paths:
            dest = output / "source" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        write_json(output / "config.json", cfg)
        write_json(output / "source_manifest.json", hashes)
        journal.append("preregistration", {"config": cfg, "source_sha256": hashes})
        banks = banks_for(cfg)
        write_json(output / "protected_banks.json", banks)
        journal.append("banks_frozen", {"sha256": digest(banks)})
        pools = {}
        costs = {arm: {"calls": 0, "seconds": 0.0, "candidates": 0} for arm in ARMS}
        for split, tasks in banks.items():
            for task in tasks:
                public = {"id": task["id"], "visible": task["visible"]}
                rows = []
                for arm in ARMS:
                    begin = time.perf_counter()
                    found = source_candidates(public, arm, {}, cfg["candidate_cap_per_arm"])
                    costs[arm]["calls"] += 1
                    costs[arm]["seconds"] += time.perf_counter() - begin
                    costs[arm]["candidates"] += len(found)
                    if not split.startswith("transfer_"):
                        for row in found:
                            row["oracle_correct"] = bool(evaluate_program(row["program"], task["visible"] + task["hidden"]))
                    rows += found
                pools[task["id"]] = rows
            journal.append("pool_split_closed", {"split": split, "sha256": digest({t["id"]: pools[t["id"]] for t in tasks})})
            print(f"{split}: {len(tasks)} tasks closed", flush=True)
        write_json(output / "candidate_pools_pretransfer.json", pools)
        policies = {}
        for index, (name, allowed) in enumerate(SETS.items()):
            genome, trace = evolve(banks["development"], pools, allowed, cfg, cfg["meta_seed"] + index)
            frozen_dev = score(banks["development"], pools, allowed, FROZEN)
            evolved_dev = score(banks["development"], pools, allowed, genome)
            frozen_adm = score(banks["admission"], pools, allowed, FROZEN)
            evolved_adm = score(banks["admission"], pools, allowed, genome)
            selected = genome if evolved_adm["correct"] >= frozen_adm["correct"] else FROZEN
            policies[name] = {"arms": allowed, "evolved_weights": genome, "selected_weights": selected,
                              "admitted": selected == genome, "trace": trace,
                              "development": {"frozen": frozen_dev, "evolved": evolved_dev},
                              "admission": {"frozen": frozen_adm, "evolved": evolved_adm}}
        journal.append("policies_frozen", {"sha256": digest(policies)})
        for split, tasks in banks.items():
            if not split.startswith("transfer_"):
                continue
            for task in tasks:
                for row in pools[task["id"]]:
                    row["oracle_correct"] = bool(evaluate_program(row["program"], task["visible"] + task["hidden"]))
            journal.append("transfer_labels_opened", {"split": split, "sha256": digest({t["id"]: pools[t["id"]] for t in tasks})})
        write_json(output / "candidate_pools.json", pools)
        final = {}
        for split in banks:
            if not split.startswith("transfer_"):
                continue
            final[split] = {}
            for name, allowed in SETS.items():
                final[split][name] = {
                    "frozen": score(banks[split], pools, allowed, FROZEN),
                    "selected": score(banks[split], pools, allowed, policies[name]["selected_weights"]),
                    "evolved": score(banks[split], pools, allowed, policies[name]["evolved_weights"]),
                }
            journal.append("transfer_scored", {"split": split, "sha256": digest(final[split])})
        result = {"status": "completed", "policies": policies, "transfer": final, "costs": costs,
                  "elapsed_seconds": time.perf_counter() - started,
                  "scope": "synthetic semantic tasks; V86 remains a separate archived encoding lane"}
        write_json(output / "results.json", result)
        if any(file_hash(ROOT / name) != value for name, value in hashes.items()):
            raise RuntimeError("source changed during pilot")
        journal.append("completed", {"sha256": digest(result)})
        seal_artifacts(output)
        return {"status": "completed", "output": str(output), "seconds": result["elapsed_seconds"],
                "transfer_counts": {split: {name: arms["selected"]["correct"] for name, arms in rows.items()}
                                    for split, rows in final.items()}}
    except BaseException as exc:
        write_json(output / "FAILED.json", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--config", default="configs/policy-transfer-2026-09-17.json")
    args = ap.parse_args()
    print(json.dumps(run(json.loads((ROOT / args.config).read_text(encoding="utf-8")), ROOT / args.output), indent=2))
