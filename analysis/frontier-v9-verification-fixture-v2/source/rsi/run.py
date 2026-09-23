from __future__ import annotations

import argparse
import copy
import datetime
import json
import platform
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

from .banks import create_banks
from .common import ROOT, Journal, digest, verify_journal, write_json
from .evaluation import Evaluator, Worker, paired_bootstrap
from .evolution import evolve, inheritance_test
from .operators import apply, initial_catalog, validate_operator
from .oracle import correct
from .search import BASE_CONFIG


def log(message):
    print(datetime.datetime.now().strftime("%H:%M:%S") + " " + message, flush=True)


def mean_by(rows, field, value_key="accuracy"):
    return {name: statistics.mean(row[value_key] for row in rows if row[field] == name) for name in sorted({row[field] for row in rows})}


def reuse_cpu_stage(source, config, bank_meta, current_manifest, journal, destination):
    source = Path(source).resolve()
    old_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if old_manifest["config_sha256"] != digest(config):
        raise ValueError("Cannot reuse CPU stage with a changed experiment configuration")
    for name in ("common", "banks", "oracle", "search", "worker", "operators", "evolution", "evaluation"):
        filename = "rsi/" + name + ".py"
        # Windows manifests use backslashes in their relative paths.
        old = {key.replace("\\", "/"): value for key, value in old_manifest["source_sha256"].items()}
        new = {key.replace("\\", "/"): value for key, value in current_manifest["source_sha256"].items()}
        if old[filename] != new[filename]:
            raise ValueError(f"CPU stage source changed: {filename}")
    if json.loads((source / "bank_manifest.json").read_text(encoding="utf-8")) != bank_meta:
        raise ValueError("Cannot reuse CPU stage with changed task banks")
    event_count = verify_journal(source / "events.jsonl")
    groups = json.loads((source / "evolution.json").read_text(encoding="utf-8"))
    for trajectories in groups.values():
        for trajectory in trajectories:
            trajectory["snapshots"] = {int(key): value for key, value in trajectory["snapshots"].items()}
    inherited = json.loads((source / "inheritance.json").read_text(encoding="utf-8"))
    expected_conditions = {"g0", "g3", "g6", "empty", "scrambled_g6"}
    if len(inherited) != config["transfer_repeats"] * len(expected_conditions) or {row["condition"] for row in inherited} != expected_conditions:
        raise ValueError("CPU inheritance stage incomplete")
    costs = {"evaluation_batches": 0, "replay_batches": 0, "search_expansions": 0, "primitive_executions": 0}
    for line in (source / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        payload = event["payload"]
        label = payload.get("label", "")
        if event["kind"] == "evaluation" and (label == "common_macro_harvest" or label.startswith(("evolution/", "random/", "inheritance/"))):
            costs["evaluation_batches"] += 1
            costs["replay_batches"] += int(payload["replay_verified"])
            repeats = 2 if payload["replay_verified"] else 1
            costs["search_expansions"] += sum(row["cost"]["expansions"] for row in payload["results"]) * repeats
            costs["primitive_executions"] += sum(row["cost"]["primitive_executions"] for row in payload["results"]) * repeats
    provenance = {"source_run": str(source), "source_journal_events": event_count, "reused_cpu_compute": costs,
                  "reason": "Neural adapter initialization fix; CPU source, configuration, task banks, and completed comparisons unchanged",
                  "artifacts_sha256": {name: digest((source / name).read_text(encoding="utf-8")) for name in ("events.jsonl", "evolution.json", "inheritance.json", "common_macros.json")}}
    for name in ("evolution.json", "inheritance.json", "common_macros.json"):
        shutil.copy2(source / name, destination / name)
    write_json(destination / "reused_cpu.json", provenance)
    journal.append("reused_cpu_stage", provenance)
    macros = json.loads((source / "common_macros.json").read_text(encoding="utf-8"))
    return groups["adaptive"], groups["random"], inherited, macros, provenance


def neural_experiment(evaluator, banks, config, evolved, run_dir, macros):
    from .neural import LocalModel, raw_scores
    model = LocalModel(config, evaluator.journal)
    final_tasks = banks["final"][:config["neural_final_tasks"]]
    task_map = {row["id"]: row for row in banks["train"]}
    sample_sets, training = {}, []
    ledgers = {}
    bootstrap_count = config.get("bootstrap_tasks", 0)
    bootstrap = None
    if bootstrap_count:
        log("Preparing identical verified bootstrap for all neural arms")
        harvested = evaluator.evaluate(banks["train"][:bootstrap_count], BASE_CONFIG, "neural/common_bootstrap", macros=macros)
        bootstrap_rows = [row for row in harvested["results"] if row["oracle_correct"]]
        if not bootstrap_rows:
            raise RuntimeError("No verified bootstrap trajectories; neural assay cannot start")
        write_json(run_dir / "verified_trajectories" / "common_bootstrap.json", bootstrap_rows)
        bootstrap = model.distill(bootstrap_rows, task_map, "bootstrap", run_dir / "adapters" / "common_bootstrap",
                                 config["neural_seed"], steps=config["bootstrap_steps"])
        model.copy_bootstrap()
        model.activate("bootstrap")
    log("Sampling initial raw Qwen baseline; hidden scores remain deferred")
    samples = model.sample(final_tasks, config["samples_per_final_task"], config["neural_seed"] + 7000)
    sample_sets["base"] = samples
    write_json(run_dir / "neural_samples" / "base.json", samples)
    seed_run = evolved[0]  # Predeclared first seed, never best-of-seeds selection.
    adaptive_config, adaptive_table = dict(BASE_CONFIG), {}
    interleaved = []
    for round_index in range(1, config["neural_rounds"] + 1):
        width = config["neural_train_tasks_per_round"]
        tasks = banks["train"][bootstrap_count + (round_index - 1) * width:bootstrap_count + round_index * width]
        if len(tasks) != width:
            raise ValueError("Not enough disjoint training tasks for configured neural rounds")
        for arm in ("search", "selftrain", "fixed_search"):
            log(f"Neural round {round_index}: {arm} generation and verified harvest")
            model.activate(arm)
            before = dict(model.ledger)
            if arm == "search" and config.get("interleave_neural_search"):
                dev_width = len(banks["development"]) // config["neural_rounds"]
                guard_width = len(banks["admission"]) // config["neural_rounds"]
                stage_banks = {"development": banks["development"][(round_index - 1) * dev_width:round_index * dev_width],
                               "admission": banks["admission"][(round_index - 1) * guard_width:round_index * guard_width]}
                meta_samples = model.sample(stage_banks["development"] + stage_banks["admission"], config["samples_per_meta_task"], config["neural_seed"] + 600 * round_index)
                write_json(run_dir / "neural_samples" / f"meta_round{round_index}.json", meta_samples)
                stage = evolve(evaluator, stage_banks, config, config["neural_seed"] + 300 * round_index,
                               initial_table=adaptive_table, initial_config=adaptive_config,
                               generations=config["generations"] // config["neural_rounds"], label=f"interleaved/round{round_index}",
                               macros=macros, proposals=meta_samples)
                adaptive_config, adaptive_table = stage["config"], stage["table"]
                interleaved.append(stage)
                write_json(run_dir / "interleaved_evolution.json", interleaved)
            proposals = model.sample(tasks, config["samples_per_train_task"], config["neural_seed"] + 100 * round_index)
            write_json(run_dir / "neural_samples" / f"{arm}_train_round{round_index}.json", proposals)
            if arm == "selftrain":
                rows = []
                for task in tasks:
                    seen = set()
                    for text in proposals[task["id"]]:
                        program = text.strip().splitlines()[0] if text.strip() else ""
                        model.ledger["oracle_string_executions"] += len(task["visible"]) + len(task["hidden"])
                        if program not in seen and correct(program, task["visible"] + task["hidden"]):
                            seen.add(program)
                            rows.append({"task_id": task["id"], "program": program, "oracle_correct": True})
                evaluator.journal.append("selftrain_harvest", {"round": round_index, "rows": rows, "samples": len(tasks) * config["samples_per_train_task"]})
            else:
                generation = round(round_index * config["generations"] / config["neural_rounds"])
                search_config = (adaptive_config if config.get("interleave_neural_search") else seed_run["snapshots"][generation]["config"]) if arm == "search" else BASE_CONFIG
                scored = evaluator.evaluate(tasks, search_config, f"neural/{arm}/round{round_index}/harvest", macros=macros, proposals=proposals)
                rows = [row for row in scored["results"] if row["oracle_correct"]]
            write_json(run_dir / "verified_trajectories" / f"{arm}_round{round_index}.json", rows)
            training.append(model.distill(rows, task_map, arm, run_dir / "adapters" / f"{arm}_round{round_index}", config["neural_seed"] + round_index))
            ledgers[f"{arm}_round{round_index}"] = {key: model.ledger[key] - before[key] for key in before}
            # Full-search curve at both rounds; control arms evaluated at final round.
            if arm == "search" or round_index == config["neural_rounds"]:
                log(f"Sampling raw {arm} round {round_index}, n=64 per task")
                name = f"{arm}_round{round_index}"
                sample_sets[name] = model.sample(final_tasks, config["samples_per_final_task"], config["neural_seed"] + 7000)
                write_json(run_dir / "neural_samples" / f"{name}.json", sample_sets[name])
    log("Testing model-proposed edit operators against protected gates")
    operator_proposals = model.propose_operators(adaptive_table or seed_run["table"], config["neural_seed"] + 9000)
    operator_results = []
    accepted_operators = []
    for index, operator in enumerate(operator_proposals):
        try:
            candidate = apply(operator, BASE_CONFIG)
            if candidate == BASE_CONFIG or any(apply(op, BASE_CONFIG) == candidate for op in initial_catalog()):
                raise ValueError("No new effective edit at the ancestor configuration")
            dev_parent = evaluator.evaluate(banks["development"], BASE_CONFIG, f"operator/{index}/dev_parent", macros=macros)
            dev_child = evaluator.evaluate(banks["development"], candidate, f"operator/{index}/dev_child", macros=macros)
            guard_parent = evaluator.evaluate(banks["admission"], BASE_CONFIG, f"operator/{index}/guard_parent", macros=macros)
            guard_child = evaluator.evaluate(banks["admission"], candidate, f"operator/{index}/guard_child", macros=macros)
            accepted = dev_child["accuracy"] > dev_parent["accuracy"] and guard_child["accuracy"] >= guard_parent["accuracy"]
            result = {"operator": operator, "accepted": accepted, "development_gain": dev_child["accuracy"] - dev_parent["accuracy"],
                      "admission_gain": guard_child["accuracy"] - guard_parent["accuracy"]}
            if accepted:
                accepted_operators.append(operator)
        except ValueError as exc:
            result = {"operator": operator, "accepted": False, "reason": str(exc)}
        evaluator.journal.append("operator_admission", result)
        operator_results.append(result)
    # Compare the catalog extension with removing it at matched edit opportunities.
    catalog_ablation = []
    if accepted_operators:
        cut = len(banks["transfer_development"]) // 2
        transfer_banks = {"development": banks["transfer_development"][:cut], "admission": banks["transfer_development"][cut:]}
        transfer_config = {**config, "generations": 6, "proposals_per_generation": config.get("transfer_proposals_per_generation", 1)}
        for seed in config["seeds"]:
            for name, catalog in (("initial_catalog", initial_catalog()), ("extended_catalog", initial_catalog() + accepted_operators)):
                trajectory = evolve(evaluator, transfer_banks, transfer_config, seed + 30000, initial_table=seed_run["table"],
                                    catalog=catalog, label=f"catalog_ablation/{name}", macros=macros)
                scored = evaluator.evaluate(banks["transfer_final"], trajectory["config"], f"catalog_ablation/{name}/{seed}/final", macros=macros)
                catalog_ablation.append({"condition": name, "seed": seed, "accuracy": scored["accuracy"], "decisions": trajectory["decisions"]})
    scores = {name: raw_scores(final_tasks, values, config["pass_k"]) for name, values in sample_sets.items()}
    model.ledger["oracle_string_executions"] += len(scores) * config["samples_per_final_task"] * sum(len(task["visible"]) + len(task["hidden"]) for task in final_tasks)
    for name, result in scores.items():
        if name != "base":
            result["pass64_minus_base"] = paired_bootstrap([row["pass_at_k"]["64"] for row in result["tasks"]],
                                                           [row["pass_at_k"]["64"] for row in scores["base"]["tasks"]])
    return {"model_id": config["model_id"], "revision": config["model_revision"], "training_seeds": [config["neural_seed"]],
            "scores": scores, "training": training, "bootstrap": bootstrap, "interleaved_evolution": interleaved,
            "compute": model.ledger, "training_arm_compute": ledgers,
            "operator_proposals_valid": len(operator_proposals), "operator_results": operator_results, "catalog_ablation": catalog_ablation,
            "limitation": "One neural training seed; optimizer steps matched when data exists, total search and oracle compute differs. No reproduction or RSI claim."}


def report(result, path):
    config, measurements = result["config"], result["search_measurements"]
    lines = ["# RSI pilot results", "", f"Run: `{result['run_id']}`", "", "This is a completed engineering pilot. It does not establish optimality, novel capability support, or recursive self-improvement.",
             "", "## Search at the fixed inference budget", "", "All rows use the same final task bank, primitive enumeration, and expansion limit. Optimization overhead is reported separately.", "",
             "| Condition | Seed | Correct / tasks | Accuracy |", "| --- | ---: | ---: | ---: |"]
    for row in measurements:
        lines.append(f"| {row['condition']} | {row['seed']} | {row['correct']} / {row['n']} | {row['accuracy']:.1%} |")
    lines += ["", "## Table-only inheritance", "", "All conditions restart from the same ancestor configuration, initial operator catalog, and common macro library. Scores are measured after equal edit opportunities on a separate transfer bank.", "",
              "| Inherited table | Mean final accuracy |", "| --- | ---: |"]
    for name, value in mean_by(result["inheritance"], "condition").items():
        lines.append(f"| {name} | {value:.1%} |")
    for comparison, values in result["inheritance_comparisons"].items():
        lines.append(f"\n{comparison}: {values['mean']:+.1%}, paired-repeat bootstrap interval [{values['ci95'][0]:+.1%}, {values['ci95'][1]:+.1%}]. These repeats share source tables and tasks; the interval is descriptive, not independent-replication evidence.")
    if result.get("neural"):
        neural = result["neural"]
        lines += ["", "## Raw model coverage after verified LoRA training", "", f"Pinned `{neural['model_id']}` at `{neural['revision']}`. Raw independent generations; no search or test-based candidate selection. One training seed.", "",
                  "| Checkpoint | pass@1 | pass@8 | pass@64 |", "| --- | ---: | ---: | ---: |"]
        for name, score in neural["scores"].items():
            values = score["pass_at_k"]
            lines.append(f"| {name} | {values['1']:.1%} | {values['8']:.1%} | {values['64']:.1%} |")
        lines += ["", "The fixed_search arm distills a fixed symbolic amplifier; search uses the evolving amplifier; selftrain uses only its own verified samples. This is inspired by search/distillation methods, not a SOAR replication. Optimizer steps are matched where verified training data exists. Total compute is not matched.", "",
                  "### Operator extension", "", f"Valid model proposals: {neural['operator_proposals_valid']}. Admitted: {sum(row['accepted'] for row in neural['operator_results'])}. Expressions use a fixed bounded metalanguage; this is not unrestricted self-rewriting or proof of level-3 RSI."]
        for row in neural["operator_results"]:
            lines.append(f"- {row['operator']['name']}: {'admitted' if row['accepted'] else 'rejected'}; {row.get('reason', 'development gain ' + str(row.get('development_gain')) + ', admission gain ' + str(row.get('admission_gain')))}")
        if neural.get("bootstrap"):
            lines += ["", f"Shared initialization: {neural['bootstrap']['rows']} independently verified search trajectories and {neural['bootstrap']['steps']} optimizer steps. The baseline above is measured after this common initialization; all three arms begin with identical adapter tensors."]
        if neural.get("interleaved_evolution"):
            lines += ["", "In the adaptive neural arm, each round's current model supplies cached proposals to three search-edit generations. The edited searcher supplies verified training solutions; distillation then changes the proposals used in the next round. The effect table and search configuration persist across rounds."]
    lines += ["", "## Integrity and costs", "", f"Journal verification: {result['journal_events']} events. Execution sensor incidents during experiment: {result['ledger']['incidents']}. Candidate batches replayed: {result['ledger']['replay_batches']}.",
              "", "```json", json.dumps(result["ledger"], indent=2), "```", "", "Logical primitive-execution counts include both original evaluation and replay. Independent oracle calls are counted separately. Raw neural grading and training-verification costs are reported in the neural section of results.json where available.",
              "", "## Limits", "", "Small task banks, a bounded DSL, fixed primitive grammar, shared generated task prior, finite hidden tests, and few independent seeds limit generalization. The protected boundary is a restricted proposal interface, not an OS sandbox for arbitrary native code. Repeated development/admission feedback is adaptive; only final banks are kept out of selection. A larger run must be separately preregistered with fresh banks and matched total compute.",
              "", "See `results.json`, `config.json`, `manifest.json`, `events.jsonl`, `verified_trajectories/`, and `adapters/` for provenance and exact measurements."]
    if result.get("reused_cpu"):
        lines += ["", "## Reused completed CPU stage", "", "The CPU stage was completed before a neural initialization guard stopped the parent run. Its source, config, bank hashes, and journal were checked before reuse. The costs above cover this continuation; add these preserved CPU costs for the full experiment:", "", "```json", json.dumps(result["reused_cpu"], indent=2), "```"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/pilot.json")
    parser.add_argument("--neural", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--reuse-cpu-run")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    run_id = args.run_id or datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "config.json", config)
    journal = Journal(run_dir / "events.jsonl")
    manifest = {"run_id": run_id, "python": sys.version, "platform": platform.platform(), "config_sha256": digest(config),
                "source_sha256": {str(path.relative_to(ROOT)): digest(path.read_text(encoding="utf-8")) for path in sorted((ROOT / "rsi").glob("*.py"))},
                "vendor_commit": subprocess.check_output(["git", "-C", str(ROOT / "vendor" / "trapdoor-loom"), "rev-parse", "HEAD"], text=True).strip()}
    write_json(run_dir / "manifest.json", manifest)
    protocol = ROOT / config.get("protocol", "EXPERIMENT.md")
    journal.append("preregistration", {"config": config, "manifest": manifest, "protocol_sha256": digest(protocol.read_text(encoding="utf-8"))})
    snapshot = run_dir / "source"
    shutil.copytree(ROOT / "rsi", snapshot / "rsi", ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("EXPERIMENT.md", config.get("protocol", "EXPERIMENT.md"), "requirements.lock.txt", "pyproject.toml"):
        shutil.copy2(ROOT / name, snapshot / name)
    log(f"Starting {run_id}; creating disjoint banks")
    banks, bank_meta = create_banks(config)
    write_json(run_dir / "protected_banks.json", banks)
    write_json(run_dir / "bank_manifest.json", bank_meta)
    worker = Worker()
    evaluator = Evaluator(journal, config, worker)
    try:
        reused_cpu = None
        if args.reuse_cpu_run:
            log("Verifying and reusing the completed CPU stage")
            evolved, random_runs, inherited, macros, reused_cpu = reuse_cpu_stage(args.reuse_cpu_run, config, bank_meta, manifest, journal, run_dir)
        else:
            log("Harvesting a common verified macro library from training tasks")
            harvest = evaluator.evaluate(banks["train"][:24], BASE_CONFIG, "common_macro_harvest")
            macros = sorted({row["program"] for row in harvest["results"] if row["oracle_correct"]})[:32]
            write_json(run_dir / "common_macros.json", macros)
            evolved, random_runs = [], []
            for seed in config["seeds"]:
                log(f"Evolving adaptive improver, seed {seed}")
                evolved.append(evolve(evaluator, banks, config, seed, macros=macros))
                log(f"Running random-edit control, seed {seed}")
                random_runs.append(evolve(evaluator, banks, config, seed, mode="random", label="random", macros=macros))
            write_json(run_dir / "evolution.json", {"adaptive": evolved, "random": random_runs})
            log("Running paired generation and intact/empty/scrambled inheritance tests")
            inherited = inheritance_test(evaluator, banks, config, evolved, macros=macros)
            write_json(run_dir / "inheritance.json", inherited)
        neural = neural_experiment(evaluator, banks, config, evolved, run_dir, macros) if args.neural else None
        if neural:
            write_json(run_dir / "neural_results.json", neural)
        log("Scoring final search holdout after all optimization")
        measurements = []
        for trajectory in evolved:
            for generation in (0, 3, 6):
                measured = evaluator.evaluate(banks["final"], trajectory["snapshots"][generation]["config"], f"final/g{generation}/{trajectory['seed']}", macros=macros)
                measurements.append({"condition": f"adaptive_g{generation}", "seed": trajectory["seed"], "accuracy": measured["accuracy"], "correct": measured["correct"], "n": measured["n"]})
        for trajectory in random_runs:
            measured = evaluator.evaluate(banks["final"], trajectory["config"], f"final/random/{trajectory['seed']}", macros=macros)
            measurements.append({"condition": "random_g6", "seed": trajectory["seed"], "accuracy": measured["accuracy"], "correct": measured["correct"], "n": measured["n"]})
        comparisons = {}
        for control in ("g0", "empty", "scrambled_g6"):
            left = [row["accuracy"] for row in inherited if row["condition"] == "g6"]
            right = [row["accuracy"] for row in inherited if row["condition"] == control]
            comparisons["g6_minus_" + control] = {**paired_bootstrap(left, right), "unit": "paired restart"}
        evaluator.assert_integrity()
        journal.append("completed", {"run_id": run_id, "ledger": evaluator.ledger})
        result = {"run_id": run_id, "config": config, "search_measurements": measurements, "inheritance": inherited,
                  "inheritance_comparisons": comparisons, "neural": neural, "ledger": evaluator.ledger, "reused_cpu": reused_cpu,
                  "journal_events": verify_journal(journal.path)}
        write_json(run_dir / "results.json", result)
        report(result, run_dir / "REPORT.md")
        write_json(ROOT / "runs" / "latest.json", {"run_id": run_id, "report": str(run_dir / "REPORT.md")})
        log(f"Completed. Report: {run_dir / 'REPORT.md'}")
        print(json.dumps({"search": mean_by(measurements, "condition"), "inheritance": mean_by(inherited, "condition"),
                          "neural": {name: row["pass_at_k"] for name, row in (neural or {}).get("scores", {}).items()}}), flush=True)
    except Exception as exc:
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        write_json(run_dir / "FAILED.json", {"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        worker.close()


if __name__ == "__main__":
    main()
