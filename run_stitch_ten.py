"""Prospective mixed-family stitch pilot with a separate V8 DSL lane."""
from __future__ import annotations
import argparse, json, random, shutil, time, traceback
from pathlib import Path

from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve
from stitch_ten import SEMANTIC_ARMS, mixed_banks, libraries_from_train, source_candidates, selected_score


def dsl_bank(cfg):
    excluded = set()
    origins = {}
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not all(isinstance(v, list) for v in rows.values()):
            continue
        for tasks in rows.values():
            excluded.update(template(t["reference"]) for t in tasks if "reference" in t)
        origins[path.relative_to(ROOT).as_posix()] = file_hash(path)
    bank, meta = create_banks({"bank_seed": cfg["dsl_seed"], "bank_counts": {"final": cfg["dsl_tasks"]},
                               "visible_examples": 3, "hidden_examples": 13, "max_atoms": cfg["dsl_max_atoms"]}, excluded)
    return bank, meta, origins


def run(cfg, output):
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "events.jsonl"); started = time.perf_counter()
    try:
        paths = sorted((ROOT / "rsi").glob("*.py")) + [ROOT / n for n in
            ("stitch_ten.py", "run_stitch_ten.py", "audit_stitch_ten.py", cfg["protocol"],
             "run_ast_v66.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py")]
        hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}
        for p in paths:
            dest = output / "source" / p.relative_to(ROOT); dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)
        write_json(output / "config.json", cfg)
        write_json(output / "source_manifest.json", hashes)
        journal.append("preregistration", {"config": cfg, "source_sha256": hashes})
        banks = mixed_banks(cfg)
        write_json(output / "protected_semantic_banks.json", banks)
        journal.append("semantic_banks_frozen", {"sha256": digest(banks)})
        libraries = libraries_from_train(banks["train"], cfg)
        write_json(output / "libraries.json", libraries)
        pools = {}; costs = {}
        for split in ("development", "admission", "final"):
            for task in banks[split]:
                pools[task["id"]] = []
                public = {"id": task["id"], "visible": task["visible"]}
                for arm in SEMANTIC_ARMS:
                    begin = time.perf_counter()
                    rows = source_candidates(public, arm, libraries, cfg["candidate_cap_per_arm"])
                    costs.setdefault(arm, {"calls": 0, "seconds": 0., "candidates": 0})
                    costs[arm]["calls"] += 1; costs[arm]["seconds"] += time.perf_counter() - begin
                    costs[arm]["candidates"] += len(rows)
                    pools[task["id"]].extend(rows)
            journal.append("pool_split_closed", {"split": split, "sha256": digest({t["id"]: pools[t["id"]] for t in banks[split]})})
            print(f"{split}: {len(banks[split])} semantic tasks closed", flush=True)
        write_json(output / "candidate_pools.json", pools)
        development = {arm: selected_score(banks["development"], pools, {arm}, [arm], 1)["correct"] for arm in SEMANTIC_ARMS}
        admission = {arm: selected_score(banks["admission"], pools, {arm}, [arm], 1)["correct"] for arm in SEMANTIC_ARMS}
        priorities = sorted(SEMANTIC_ARMS, key=lambda arm: (-development[arm], -admission[arm], arm))
        # Admission checks the proposed router against the best native arm.
        native = priorities[0]
        route_adm = selected_score(banks["admission"], pools, set(SEMANTIC_ARMS), priorities, 1)
        route = priorities if route_adm["correct"] >= admission[native] else [native]
        random_priority = list(SEMANTIC_ARMS); random.Random(cfg["bank_seed"] + 77).shuffle(random_priority)
        journal.append("optimization_closed", {"development": development, "admission": admission,
                       "priorities": priorities, "selected_priorities": route, "native": native})
        final = {arm: selected_score(banks["final"], pools, {arm}, [arm], 1) for arm in SEMANTIC_ARMS}
        final["stitched"] = selected_score(banks["final"], pools, set(route), route, 1)
        final["random_router"] = selected_score(banks["final"], pools, set(SEMANTIC_ARMS), random_priority, 1)
        final["frozen_direct"] = final["v73"]
        for arm in SEMANTIC_ARMS:
            allowed = set(SEMANTIC_ARMS) - {arm}
            priority = [a for a in route if a in allowed] or [a for a in priorities if a in allowed]
            final["minus_" + arm] = selected_score(banks["final"], pools, allowed, priority, 1)
        dsl, dsl_meta, origins = dsl_bank(cfg)
        write_json(output / "protected_banks.json", dsl)
        write_json(output / "dsl_bank_manifest.json", dsl_meta)
        write_json(output / "dsl_prior_hashes.json", origins)
        journal.append("dsl_bank_frozen", {"sha256": digest(dsl), "prior_sha256": digest(origins)})
        dsl_rows = []; dsl_cost = {"expansions": 0, "primitive_executions": 0}
        for task in dsl["final"]:
            public = public_task(task)
            base = solve(public, BASE_CONFIG, cfg["dsl_budget"], cfg["dsl_max_atoms"], [], [], pool_mode="baseline")
            corrected = solve(public, BASE_CONFIG, cfg["dsl_budget"], cfg["dsl_max_atoms"], [], [], pool_mode="partial_empty")
            replay = solve(public, BASE_CONFIG, cfg["dsl_budget"], cfg["dsl_max_atoms"], [], [], pool_mode="partial_empty")
            if corrected != replay: raise RuntimeError("V8 replay mismatch")
            for row in (base, corrected, replay):
                for key in dsl_cost: dsl_cost[key] += row["cost"][key]
            dsl_rows.append({"task_id": task["id"], "baseline": base, "v8": corrected,
                             "baseline_correct": correct(base["program"], task["visible"] + task["hidden"]),
                             "v8_correct": correct(corrected["program"], task["visible"] + task["hidden"])})
        result = {"status": "completed", "semantic_final": final, "development": development,
                  "admission": admission, "priority": priorities, "selected_priority": route,
                  "native": native, "semantic_compute": costs, "dsl_final": dsl_rows,
                  "dsl_cost": dsl_cost, "elapsed_seconds": time.perf_counter() - started,
                  "scope": "two task lanes; no pooled accuracy or RSI claim"}
        write_json(output / "results.json", result)
        if any(file_hash(ROOT / name) != value for name, value in hashes.items()):
            raise RuntimeError("source changed during pilot")
        journal.append("completed", {"sha256": digest(result)})
        seal_artifacts(output)
        return {"status": "completed", "semantic_final": {k: v["correct"] for k, v in final.items()},
                "dsl_baseline": sum(r["baseline_correct"] for r in dsl_rows),
                "dsl_v8": sum(r["v8_correct"] for r in dsl_rows), "elapsed_seconds": result["elapsed_seconds"]}
    except BaseException as exc:
        write_json(output / "FAILED.json", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("output"); ap.add_argument("--config", default="configs/stitch-ten-pilot.json"); args = ap.parse_args()
    print(json.dumps(run(json.loads((ROOT / args.config).read_text()), ROOT / args.output), indent=2))
