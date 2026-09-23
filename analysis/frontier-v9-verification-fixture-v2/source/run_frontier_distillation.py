"""Frozen verified harvest, controlled task-balanced neural updates, deferred finals."""
import argparse
import json
import platform
import shutil
import sys
import time
import traceback
from pathlib import Path

from audit_results import published_correct
from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.frontier_training import FrontierModel, build_pool, harvest_arm
from rsi.neural import adapter_hash
from rsi.oracle import correct
from rsi.retention import coverage_decision, measure, resolve_update
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve


def advancement(scores, selected, config):
    rows = []
    for seed in config["training_seeds"]:
        key = str(seed)
        get = lambda name: scores[name]["pass_at_k"]["64"]
        state = selected[key]
        rows.append({"seed": seed, "frontier_round2": get(state["corrected_frontier"]["2"]),
                     "frontier_round1": get(state["corrected_frontier"]["1"]),
                     "selected_round2": get(state["corrected_selected"]["2"]),
                     "initial": get(f"s{seed}_initial"), "base": get(f"s{seed}_base")})
    mean = lambda name: sum(r[name] for r in rows) / len(rows)
    delta = mean("frontier_round2") - mean("selected_round2")
    positive = sum(r["frontier_round2"] > r["selected_round2"] for r in rows)
    criteria = {"positive_mean_primary_contrast": delta > 0, "positive_in_two_seeds": positive >= 2,
                "above_frozen_bootstrap": mean("frontier_round2") > mean("initial"),
                "above_unadapted_base": mean("frontier_round2") > mean("base"),
                "round_two_retains_round_one_mean": mean("frontier_round2") >= mean("frontier_round1")}
    return {"passed": all(criteria.values()), "criteria": criteria, "primary_delta": delta,
            "positive_seeds": positive, "per_seed": rows, "meaning": "Engineering advancement screen; not demonstrated RSI"}


def run(config, root):
    root.mkdir(parents=True, exist_ok=False)
    journal = Journal(root / "events.jsonl")
    started = time.perf_counter()
    try:
        assert config["arms"] == ["baseline_selected", "corrected_selected", "corrected_first_verified", "corrected_frontier"]
        source = ROOT / config["source_run"]
        assert json.loads((source / "audit.json").read_text())["status"] == "passed"
        origin_manifest = json.loads((source / "artifact_manifest.json").read_text())
        inputs = ["protected_banks.json", "verified_trajectories/common_bootstrap.json", config["checkpoint_relative_path"]]
        for name in inputs:
            assert file_hash(source / name) == origin_manifest[name]["sha256"]
        previous_tasks = json.loads((source / "protected_banks.json").read_text())["train"]
        anchors = json.loads((source / "verified_trajectories/common_bootstrap.json").read_text())
        anchor_ids = {r["task_id"] for r in anchors}
        anchor_tasks = [t for t in previous_tasks if t["id"] in anchor_ids]
        exclusions, origins = set(), {}
        for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
            old = json.loads(path.read_text())
            exclusions.update(template(t["reference"]) for tasks in old.values() for t in tasks)
            origins[str(path.relative_to(ROOT))] = file_hash(path)
        macros = json.loads((ROOT / config["macro_source"]).read_text())
        paths = list((ROOT / "rsi").glob("*.py")) + [ROOT / name for name in
            ("run_frontier_distillation.py", "audit_frontier_distillation.py", "audit_retention.py", "audit_results.py",
             config["protocol"], "research-frontier-distillation-2026-09-16.md", "requirements.lock.txt")]
        paths += [ROOT / "vendor/trapdoor-loom" / name for name in ("dsl.py", "parse.py", "trapdoor.py")]
        hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}
        for path in paths:
            dest = root / "source" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        manifest = {"config_sha256": digest(config), "source_sha256": hashes, "python": sys.version, "platform": platform.platform(),
                    "input_hashes": {name: file_hash(source / name) for name in inputs},
                    "macro_source_sha256": file_hash(ROOT / config["macro_source"])}
        write_json(root / "config.json", config)
        write_json(root / "manifest.json", manifest)
        write_json(root / "prior_bank_exclusions.json", {"source_hashes": origins, "templates": sorted(exclusions)})
        write_json(root / "common_macros.json", macros)
        journal.append("preregistration", {"config": config, "manifest": manifest, "exclusions_sha256": digest(sorted(exclusions))})
        banks, metadata = create_banks(config, exclusions)
        banks["anchors"] = anchor_tasks
        metadata["anchors"] = {"count": len(anchor_tasks), "sha256": digest(anchor_tasks), "source": config["source_run"]}
        write_json(root / "protected_banks.json", banks)
        write_json(root / "bank_manifest.json", metadata)
        write_json(root / "anchors.json", anchors)
        journal.append("bank_frozen", {"metadata": metadata, "sha256": digest(banks)})
        task_map = {t["id"]: t for split, tasks in banks.items() if split.startswith("harvest_") or split == "anchors" for t in tasks}
        # Verify common anchors before they can enter any training pool.
        build_pool(anchors, [], task_map)
        harvest, raw_harvest = {}, []
        harvest_started = time.perf_counter()
        for round_index in range(1, config["rounds"] + 1):
            split = f"harvest_round{round_index}"
            harvest[split] = {arm: [] for arm in config["arms"]}
            for task in banks[split]:
                for mode in ("baseline", "partial_empty"):
                    request = {"task": public_task(task), "config": BASE_CONFIG, "budget": config["search_budget"],
                               "max_atoms": config["max_atoms"], "macros": macros, "mode": mode}
                    details, replay_details = {}, {}
                    args = (request["task"], BASE_CONFIG, config["search_budget"], config["max_atoms"], macros, [])
                    first = solve(*args, diagnostics=details, pool_mode=mode)
                    replay = solve(*args, diagnostics=replay_details, pool_mode=mode)
                    assert canonical(first) == canonical(replay) and canonical(details) == canonical(replay_details)
                    frontier = []
                    for item in details["frontier"]:
                        grade = correct(item["program"], task["visible"] + task["hidden"])
                        assert grade == published_correct(item["program"], task["visible"] + task["hidden"])
                        frontier.append({**item, "oracle_correct": grade})
                    record = {"split": split, "task_id": task["id"], "request": request, "request_sha256": digest(request),
                              "result": first, "details_sha256": digest(details), "replay_result_sha256": digest(replay),
                              "replay_details_sha256": digest(replay_details), "frontier": frontier}
                    raw_harvest.append(record)
                    journal.append("harvest_search", record)
                    for arm in config["arms"]:
                        if (arm == "baseline_selected") != (mode == "baseline"):
                            continue
                        harvest[split][arm].extend({"task_id": task["id"], "program": item["program"], "oracle_correct": True}
                                                   for item in harvest_arm(frontier, arm))
            print(f"Harvest round {round_index}: " + str({a: (len(r), len({x['task_id'] for x in r})) for a, r in harvest[split].items()}), flush=True)
        write_json(root / "harvest_searches.json", raw_harvest)
        write_json(root / "harvest.json", harvest)
        acquisition = {"seconds": time.perf_counter() - harvest_started,
                       "searches": len(raw_harvest), "exact_replays": len(raw_harvest),
                       "cost_including_replay": {k: 2 * sum(r["result"]["cost"][k] for r in raw_harvest) for k in raw_harvest[0]["result"]["cost"]},
                       "grade_example_upper_bound": 2 * sum(len(r["frontier"]) * (config["visible_examples"] + config["hidden_examples"]) for r in raw_harvest),
                       "logical_arm_search_cost_including_replay": {arm: {k: 2 * sum(r["result"]["cost"][k] for r in raw_harvest if r["request"]["mode"] == ("baseline" if arm == "baseline_selected" else "partial_empty")) for k in raw_harvest[0]["result"]["cost"]} for arm in config["arms"]}}
        journal.append("harvest_closed", {"sha256": digest(harvest), "acquisition": acquisition})
        pools = {}
        for arm in config["arms"]:
            for round_index in range(1, config["rounds"] + 1):
                rows = [r for round_number in range(1, round_index + 1) for r in harvest[f"harvest_round{round_number}"][arm]]
                pool = build_pool(anchors, rows, task_map)
                pools[(arm, round_index)] = pool
                write_json(root / "training_pools" / f"{arm}_round{round_index}.json", pool)
        from safetensors.torch import load_file
        model = FrontierModel(config, journal)
        initial_state = load_file(str(source / inputs[-1]))
        model.restore("bootstrap", initial_state)
        initial_hash = adapter_hash(initial_state)
        model.save_adapter("bootstrap", root / "adapters" / "initial")
        journal.append("initial_checkpoint", {"tensor_sha256": initial_hash, "file_sha256": manifest["input_hashes"][inputs[-1]], "path": str(source / inputs[-1])})
        journal.append("runtime", {"torch": model.torch.__version__, "cuda": model.torch.version.cuda,
                                   "gpu": model.torch.cuda.get_device_name(config["device"])})
        sample_cache, final_refs, selected, changes = {}, {}, {}, []
        measurement = {"program_checks": 0, "string_check_upper_bound": 0}

        def scored(tasks, outputs):
            measurement["program_checks"] += sum(len(outputs[t["id"]]) for t in tasks)
            measurement["string_check_upper_bound"] += sum(len(outputs[t["id"]]) * (len(t["visible"]) + len(t["hidden"])) for t in tasks)
            return measure(tasks, outputs, config["pass_k"])

        def sample_saved(label, split, adapter, checkpoint, seed):
            public = [public_task(t) for t in banks[split]]
            if adapter is not None:
                assert adapter_hash(model.snapshot(adapter)) == checkpoint
            request = {"split": split, "tasks": public, "checkpoint_sha256": checkpoint, "seed": seed,
                       "n": config["samples_per_task"], "model_id": config["model_id"], "revision": config["model_revision"],
                       "generation_batch_size": config["generation_batch_size"], "max_new_tokens": config["max_new_tokens"],
                       "temperature": 0.8, "top_p": 0.95, "top_k": 20}
            key = digest(request)
            if key in sample_cache:
                ref, outputs = sample_cache[key]
                journal.append("sampling_reuse", {"label": label, "request_sha256": key, "source": ref})
                return ref, outputs
            model.activate(adapter)
            before = dict(model.ledger)
            print(f"Sampling {label}: {len(public)} tasks x {config['samples_per_task']}", flush=True)
            outputs = model.sample(public, config["samples_per_task"], seed)
            cost = {k: model.ledger[k] - before[k] for k in before}
            payload = {"request": request, "request_sha256": key, "outputs": outputs, "cost": cost,
                       "generation_trace": model.last_generation_trace}
            path = "samples/" + label + ".json"
            write_json(root / path, payload)
            ref = {"path": path, "sha256": digest(payload), "request_sha256": key}
            sample_cache[key] = (ref, outputs)
            journal.append("sampled", {"label": label, "ref": ref, "cost": cost})
            return ref, outputs

        for seed in config["training_seeds"]:
            selected[str(seed)] = {}
            final_seed = seed + 7000
            for name, adapter, checkpoint in (("base", None, digest([config["model_id"], config["model_revision"], "no_adapter"])), ("initial", "bootstrap", initial_hash)):
                label = f"s{seed}_{name}"
                ref, _ = sample_saved(label, "final", adapter, checkpoint, final_seed)
                final_refs[label] = ref
            for arm in config["arms"]:
                model.restore("search", initial_state)
                selected_name = f"s{seed}_initial"
                selected[str(seed)][arm] = {}
                for round_index in range(1, config["rounds"] + 1):
                    change_id = f"s{seed}_{arm}_round{round_index}"
                    split = f"validation_round{round_index}"
                    validation_seed = seed + 8000 + round_index
                    parent = model.snapshot("search")
                    parent_ref, parent_outputs = sample_saved(change_id + "_parent", split, "search", adapter_hash(parent), validation_seed)
                    parent_score = scored(banks[split], parent_outputs)
                    pool = pools[(arm, round_index)]
                    proposal = {"change_id": change_id, "arm": arm, "seed": seed, "round": round_index,
                                "pool_sha256": digest(pool), "parent_sha256": adapter_hash(parent), "parent_checkpoint": selected_name,
                                "validation_split": split, "final_feedback_used": False,
                                "hypothesis": "Verified frontier task coverage and within-task programs can transfer into neural coverage under common retention"}
                    journal.append("change_proposed", proposal)
                    before = dict(model.ledger)
                    training = model.train_balanced(pool, task_map, "search", root / "adapters" / (change_id + "_candidate"), seed + round_index, change_id)
                    training_cost = {k: model.ledger[k] - before[k] for k in before}
                    candidate_hash = adapter_hash(model.snapshot("search"))
                    candidate_ref, candidate_outputs = sample_saved(change_id + "_candidate_validation", split, "search", candidate_hash, validation_seed)
                    candidate_score = scored(banks[split], candidate_outputs)
                    decision = coverage_decision(parent_score, candidate_score)
                    final_ref, _ = sample_saved(change_id + "_candidate_final", "final", "search", candidate_hash, final_seed)
                    final_refs[change_id] = final_ref
                    decision = resolve_update(model, "search", parent, decision, True)
                    if decision["accepted"]:
                        selected_name = change_id
                    selected[str(seed)][arm][str(round_index)] = selected_name
                    model.save_adapter("search", root / "adapters" / (change_id + "_selected"))
                    validation = {"parent_ref": parent_ref, "candidate_ref": candidate_ref,
                                  "parent": parent_score, "candidate": candidate_score, "seed": validation_seed}
                    write_json(root / "validation" / (change_id + ".json"), validation)
                    record = {**proposal, "training": training, "training_cost": training_cost,
                              "validation_sha256": digest(validation), "decision": decision, "selected_checkpoint": selected_name}
                    changes.append(record)
                    write_json(root / "changes" / (change_id + ".json"), record)
                    journal.append("change_resolved", record)
                    write_json(root / "progress.json", {"resolved": len(changes), "total": len(config["training_seeds"]) * len(config["arms"]) * config["rounds"],
                              "last_change": change_id, "selected": selected})
                    print(f"{change_id}: accepted={decision['accepted']}, admission lost={len(decision['lost_task_ids'])}, gained={len(decision['gained_task_ids'])}", flush=True)
        journal.append("optimization_closed", {"selected": selected, "changes": len(changes)})
        write_json(root / "final_refs.json", final_refs)
        scores = {}
        for name, ref in final_refs.items():
            outputs = json.loads((root / ref["path"]).read_text())["outputs"]
            scores[name] = scored(banks["final"], outputs)
        effects = {r["change_id"]: coverage_decision(scores[r["parent_checkpoint"]], scores[r["change_id"]]) for r in changes}
        result = {"status": "completed", "scores": scores, "selected": selected, "changes": changes,
                  "candidate_final_effects": effects, "screen": advancement(scores, selected, config),
                  "compute": model.ledger, "measurement_cost": measurement, "acquisition": acquisition,
                  "elapsed_seconds": time.perf_counter() - started,
                  "limitations": ["fixed harvest", "three training seeds with common bank and bootstrap", "finite admission gate", "not total-compute matched", "not RSI"]}
        assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
        write_json(root / "results.json", result)
        journal.append("completed", {"results_sha256": digest(result)})
        seal_artifacts(root)
        print(json.dumps({"screen": result["screen"], "elapsed_seconds": result["elapsed_seconds"], "compute": result["compute"]}, indent=2))
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        journal.append("failed", failure)
        write_json(root / "FAILED.json", failure)
        raise


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Assertions must remain enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--config", default="configs/frontier-v9.json")
    args = parser.parse_args()
    run(json.loads(Path(args.config).read_text()), Path(args.output))
