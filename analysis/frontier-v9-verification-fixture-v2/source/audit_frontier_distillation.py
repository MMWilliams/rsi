"""Independent grades, harvest selection, balanced draws and checkpoint decisions."""
import argparse
import json
import math
import random
from pathlib import Path

from audit_retention import check_score as check_basic_score
from rsi.banks import create_banks, template
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.neural import adapter_hash, user_prompt
from rsi.retention_run import file_hash
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve
from dsl import render
from parse import parse, ParseError
from rsi.oracle import correct as oracle_correct, outcomes as oracle_outcomes


def check_score(tasks, samples, score):
    checked = check_basic_score(tasks, samples, score)
    syntax_total = behavior_total = parseable_total = 0
    for task, row in zip(tasks, score["tasks"]):
        syntaxes, behaviors, parseable = set(), set(), 0
        for text in samples[task["id"]]:
            program = text.strip().splitlines()[0] if text.strip() else ""
            try:
                parsed = parse(program)
                syntaxes.add(render(parsed))
                parseable += 1
                behaviors.add(digest(oracle_outcomes(program, task["visible"])))
            except (ParseError, ValueError, TypeError, RecursionError, AttributeError):
                pass
        assert row["distinct_parseable_programs"] == len(syntaxes) and row["parseable"] == parseable
        assert row["distinct_visible_behaviors"] == len(behaviors)
        syntax_total += len(syntaxes)
        behavior_total += len(behaviors)
        parseable_total += parseable
    assert math.isclose(score["mean_distinct_parseable_programs"], syntax_total / len(tasks), abs_tol=1e-12)
    assert math.isclose(score["mean_distinct_visible_behaviors"], behavior_total / len(tasks), abs_tol=1e-12)
    assert math.isclose(score["parseable_fraction"], parseable_total / checked, abs_tol=1e-12)
    return checked


def independent_pool(anchors, harvest, tasks):
    assert not {r["task_id"] for r in anchors} & {r["task_id"] for r in harvest}
    rows = {}
    for name, values in (("anchor", anchors), ("harvest", harvest)):
        for row in values:
            task = tasks[row["task_id"]]
            assert row["oracle_correct"] is True and oracle_correct(row["program"], task["visible"] + task["hidden"])
            program = render(parse(row["program"]))
            rows[(name, row["task_id"], program)] = {"task_id": row["task_id"], "program": program, "oracle_correct": True, "stratum": name}
    return [rows[k] for k in sorted(rows)]


def check_decision(parent, candidate, decision):
    old = {r["id"] for r in parent["tasks"] if r["correct"]}
    new = {r["id"] for r in candidate["tasks"] if r["correct"]}
    d64 = candidate["pass_at_k"]["64"] - parent["pass_at_k"]["64"]
    d1 = candidate["pass_at_k"]["1"] - parent["pass_at_k"]["1"]
    reasons = []
    if old - new:
        reasons.append("previously_solved_validation_tasks_lost")
    if d64 < -1e-12:
        reasons.append("large_k_validation_regression")
    if d1 < -1e-12:
        reasons.append("pass1_validation_regression")
    if d64 <= 1e-12 and d1 <= 1e-12:
        reasons.append("no_measured_validation_gain")
    assert decision["eligible"] == (not reasons)
    assert decision["reasons"] == (reasons or ["coverage_retained_and_measured_gain"])
    assert decision["lost_task_ids"] == sorted(old - new) and decision["gained_task_ids"] == sorted(new - old)
    assert math.isclose(decision["pass_k_delta"], d64, abs_tol=1e-12)
    assert math.isclose(decision["pass1_delta"], d1, abs_tol=1e-12)


def audit(root):
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    artifacts = read("artifact_manifest.json")
    assert set(artifacts) == {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name not in ("artifact_manifest.json", "audit.json")}
    for name, entry in artifacts.items():
        assert file_hash(root / name) == entry["sha256"] and (root / name).stat().st_size == entry["bytes"]
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    count = verify_journal(root / "events.jsonl")
    assert events[0]["kind"] == "preregistration" and events[-1]["kind"] == "completed"
    config, manifest, result = read("config.json"), read("manifest.json"), read("results.json")
    assert manifest["config_sha256"] == digest(config)
    assert events[0]["payload"]["manifest"] == manifest and events[0]["payload"]["config"] == config
    for name, value in manifest["source_sha256"].items():
        assert file_hash(root / "source" / name) == value
        assert file_hash(ROOT / name) == value, "Audit needs archived source version"
    source = ROOT / config["source_run"]
    for name, value in manifest["input_hashes"].items():
        assert file_hash(source / name) == value
    assert read("common_macros.json") == json.loads((ROOT / config["macro_source"]).read_text())
    assert file_hash(ROOT / config["macro_source"]) == manifest["macro_source_sha256"]
    previous, exclusions = read("prior_bank_exclusions.json"), set()
    for name, value in previous["source_hashes"].items():
        assert file_hash(ROOT / name) == value
        old = json.loads((ROOT / name).read_text())
        exclusions.update(template(t["reference"]) for rows in old.values() for t in rows)
    assert previous["templates"] == sorted(exclusions)
    assert events[0]["payload"]["exclusions_sha256"] == digest(sorted(exclusions))
    banks, metadata = create_banks(config, exclusions)
    anchors = read("anchors.json")
    assert anchors == json.loads((source / "verified_trajectories/common_bootstrap.json").read_text())
    old_tasks = json.loads((source / "protected_banks.json").read_text())["train"]
    banks["anchors"] = [t for t in old_tasks if t["id"] in {r["task_id"] for r in anchors}]
    metadata["anchors"] = {"count": len(banks["anchors"]), "sha256": digest(banks["anchors"]), "source": config["source_run"]}
    assert read("protected_banks.json") == banks and read("bank_manifest.json") == metadata
    assert next(e["payload"] for e in events if e["kind"] == "bank_frozen") == {"metadata": metadata, "sha256": digest(banks)}
    tasks = {t["id"]: t for split, rows in banks.items() if split.startswith("harvest_") or split == "anchors" for t in rows}
    raw = read("harvest_searches.json")
    expected = [(f"harvest_round{r}", task, mode) for r in range(1, config["rounds"] + 1) for task in banks[f"harvest_round{r}"] for mode in ("baseline", "partial_empty")]
    assert len(raw) == len(expected)
    assert [e["payload"] for e in events if e["kind"] == "harvest_search"] == raw
    harvest = {f"harvest_round{r}": {a: [] for a in config["arms"]} for r in range(1, config["rounds"] + 1)}
    for row, (split, task, mode) in zip(raw, expected):
        request = {"task": {"id": task["id"], "visible": task["visible"]}, "config": BASE_CONFIG, "budget": config["search_budget"],
                   "max_atoms": config["max_atoms"], "macros": read("common_macros.json"), "mode": mode}
        assert row["request"] == request and row["request_sha256"] == digest(request)
        assert row["split"] == split and row["task_id"] == task["id"]
        details = {}
        repeated = solve(request["task"], BASE_CONFIG, request["budget"], request["max_atoms"], request["macros"], [], diagnostics=details, pool_mode=mode)
        assert repeated == row["result"] and row["replay_result_sha256"] == digest(repeated)
        assert row["details_sha256"] == row["replay_details_sha256"] == digest(details)
        graded = [{**f, "oracle_correct": oracle_correct(f["program"], task["visible"] + task["hidden"])} for f in details["frontier"]]
        assert graded == row["frontier"]
        for arm in config["arms"]:
            if (arm == "baseline_selected") != (mode == "baseline"):
                continue
            good = [f for f in graded if f["oracle_correct"]]
            if arm in ("baseline_selected", "corrected_selected"):
                chosen = graded[:1] if graded and graded[0]["oracle_correct"] else []
            elif arm == "corrected_first_verified":
                chosen = good[:1]
            else:
                chosen = good
            harvest[split][arm].extend({"task_id": task["id"], "program": f["program"], "oracle_correct": True} for f in chosen)
    assert harvest == read("harvest.json")
    harvest_close = next(e for e in events if e["kind"] == "harvest_closed")
    assert harvest_close["payload"]["sha256"] == digest(harvest)
    acquisition = result["acquisition"]
    assert acquisition == harvest_close["payload"]["acquisition"]
    assert acquisition["searches"] == acquisition["exact_replays"] == len(raw)
    assert acquisition["cost_including_replay"] == {k: 2 * sum(r["result"]["cost"][k] for r in raw) for k in raw[0]["result"]["cost"]}
    assert acquisition["grade_example_upper_bound"] == 2 * sum(len(r["frontier"]) * (config["visible_examples"] + config["hidden_examples"]) for r in raw)
    for arm in config["arms"]:
        assert acquisition["logical_arm_search_cost_including_replay"][arm] == {k: 2 * sum(r["result"]["cost"][k] for r in raw if r["request"]["mode"] == ("baseline" if arm == "baseline_selected" else "partial_empty")) for k in raw[0]["result"]["cost"]}
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(config["model_id"], revision=config["model_revision"], local_files_only=True)
    tokenizer.pad_token = tokenizer.eos_token
    sample_files, samples_by_request = {}, {}
    for event in events:
        if event["kind"] == "sampled":
            ref = event["payload"]["ref"]
            payload = read(ref["path"])
            assert digest(payload) == ref["sha256"] and digest(payload["request"]) == ref["request_sha256"] == payload["request_sha256"]
            request = payload["request"]
            assert request["tasks"] == [{"id": t["id"], "visible": t["visible"]} for t in banks[request["split"]]]
            assert request["n"] == config["samples_per_task"]
            assert set(payload["outputs"]) == {t["id"] for t in banks[request["split"]]}
            assert all(len(x) == request["n"] for x in payload["outputs"].values())
            assert request["model_id"] == config["model_id"] and request["revision"] == config["model_revision"]
            assert request["generation_batch_size"] == config["generation_batch_size"] and request["max_new_tokens"] == config["max_new_tokens"]
            assert (request["temperature"], request["top_p"], request["top_k"]) == (0.8, 0.95, 20)
            assert payload["cost"] == event["payload"]["cost"]
            lengths = []
            for task in request["tasks"]:
                prompt = tokenizer.apply_chat_template([{"role": "user", "content": user_prompt(task["visible"])}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
                lengths.extend([len(tokenizer(prompt, add_special_tokens=False).input_ids)] * request["n"])
            token_rows = []
            for trace in payload["generation_trace"]:
                assert trace["offset"] == len(token_rows)
                size = min(config["generation_batch_size"], len(lengths) - len(token_rows))
                assert len(trace["completion_ids"]) == size
                assert trace["prompt_lengths"] == lengths[len(token_rows):len(token_rows) + size]
                assert all(len(ids) <= config["max_new_tokens"] for ids in trace["completion_ids"])
                token_rows.extend(trace["completion_ids"])
            assert len(token_rows) == len(lengths)
            actual_text = [text for task in request["tasks"] for text in payload["outputs"][task["id"]]]
            assert tokenizer.batch_decode(token_rows, skip_special_tokens=True) == actual_text
            assert payload["cost"]["generated_tokens"] == sum(token != tokenizer.pad_token_id for ids in token_rows for token in ids)
            assert payload["cost"]["prompt_tokens"] == sum(lengths)
            assert ref["request_sha256"] not in samples_by_request
            samples_by_request[ref["request_sha256"]] = ref
            sample_files[ref["path"]] = payload
        elif event["kind"] == "sampling_reuse":
            p = event["payload"]
            assert p["source"] == samples_by_request[p["request_sha256"]]

    def sample_ref(ref, split, checkpoint, seed):
        payload = sample_files[ref["path"]]
        assert digest(payload) == ref["sha256"] and payload["request_sha256"] == ref["request_sha256"]
        assert payload["request"]["split"] == split and payload["request"]["checkpoint_sha256"] == checkpoint and payload["request"]["seed"] == seed
        return payload["outputs"]

    from safetensors.torch import load_file
    initial = adapter_hash(load_file(str(root / "adapters/initial/bootstrap/adapter_model.safetensors")))
    origin = adapter_hash(load_file(str(source / config["checkpoint_relative_path"])))
    assert initial == origin
    assert next(e["payload"] for e in events if e["kind"] == "initial_checkpoint")["tensor_sha256"] == initial
    resolved = [e for e in events if e["kind"] == "change_resolved"]
    proposed = [e for e in events if e["kind"] == "change_proposed"]
    assert [e["payload"] for e in resolved] == result["changes"]
    expected_changes = [(s, a, r) for s in config["training_seeds"] for a in config["arms"] for r in range(1, config["rounds"] + 1)]
    assert len(resolved) == len(proposed) == len(expected_changes)
    closed = next(e for e in events if e["kind"] == "optimization_closed")
    assert all(harvest_close["seq"] < p["seq"] < r["seq"] < closed["seq"] for p, r in zip(proposed, resolved))
    selected, state = {}, {}
    checked = training_rows = steps_checked = 0
    refs = read("final_refs.json")
    expected_names = {f"s{s}_{name}" for s in config["training_seeds"] for name in ("initial", "base")}
    expected_names |= {f"s{s}_{a}_round{r}" for s, a, r in expected_changes}
    assert set(refs) == set(result["scores"]) == expected_names
    for seed in config["training_seeds"]:
        selected[str(seed)] = {a: {} for a in config["arms"]}
        for arm in config["arms"]:
            state[(seed, arm)] = (initial, f"s{seed}_initial")
        for name, checkpoint in (("initial", initial), ("base", digest([config["model_id"], config["model_revision"], "no_adapter"]))):
            label = f"s{seed}_{name}"
            checked += check_score(banks["final"], sample_ref(refs[label], "final", checkpoint, seed + 7000), result["scores"][label])
    for change, proposal, (seed, arm, round_index) in zip(result["changes"], proposed, expected_changes):
        name = f"s{seed}_{arm}_round{round_index}"
        assert change["change_id"] == name and change["seed"] == seed and change["arm"] == arm and change["round"] == round_index
        assert all(change[k] == v for k, v in proposal["payload"].items()) and change["final_feedback_used"] is False
        assert change == read("changes/" + name + ".json")
        parent_hash, parent_name = state[(seed, arm)]
        assert change["parent_sha256"] == parent_hash and change["parent_checkpoint"] == parent_name
        collected = [r for i in range(1, round_index + 1) for r in harvest[f"harvest_round{i}"][arm]]
        pool = independent_pool(anchors, collected, tasks)
        assert pool == read(f"training_pools/{arm}_round{round_index}.json")
        assert digest(pool) == change["pool_sha256"] == change["training"]["rows_sha256"]
        training_rows += len(pool)
        tr = change["training"]
        assert tr["parent_sha256"] == parent_hash and tr["seed"] == seed + round_index
        assert tr["change_id"] == name and tr["rows"] == len(pool) and tr["task_ids"] == [r["task_id"] for r in pool]
        step_events = [e["payload"] for e in events if e["kind"] == "optimizer_step" and e["payload"]["change_id"] == name]
        groups = {key: {} for key in ("anchor", "harvest")}
        for index, row in enumerate(pool):
            groups[row["stratum"]].setdefault(row["task_id"], []).append(index)
        expected_steps = config["lora_steps"] if all(groups.values()) else 0
        assert len(step_events) == tr["steps"] == expected_steps
        task_rngs = {"anchor": random.Random(seed + round_index), "harvest": random.Random((seed + round_index) ^ 0xA71C)}
        program_rng = random.Random((seed + round_index) ^ 0xB93D)
        schedule = []
        completion_lengths = [len(tokenizer(row["program"] + tokenizer.eos_token, add_special_tokens=False).input_ids) for row in pool]
        for step, event in enumerate(step_events, 1):
            expected_draw = []
            for position in range(config["lora_batch_size"]):
                stratum = "anchor" if position < config["anchor_per_batch"] else "harvest"
                ids = sorted(groups[stratum])
                task_id = ids[task_rngs[stratum].randrange(len(ids))]
                indices = groups[stratum][task_id]
                expected_draw.append(indices[program_rng.randrange(len(indices))])
            assert event["row_indices"] == expected_draw and event["step"] == step and event["seed"] == seed + round_index
            assert event["rows_sha256"] == digest(pool) and event["learning_rate"] == config["lora_learning_rate"]
            assert event["anchor_draws"] == config["anchor_per_batch"] and event["harvest_draws"] == config["lora_batch_size"] - config["anchor_per_batch"]
            assert event["supervised_tokens"] == sum(completion_lengths[i] for i in expected_draw)
            assert math.isfinite(event["loss"]) and math.isfinite(event["gradient_norm_before_clip"])
            schedule.append(expected_draw)
        assert tr["schedule_sha256"] == digest(schedule) and tr["losses"] == [e["loss"] for e in step_events]
        steps_checked += len(step_events)
        decision = change["decision"]
        for stage in ("candidate", "selected"):
            actual = adapter_hash(load_file(str(root / "adapters" / (name + "_" + stage) / "amplified/adapter_model.safetensors")))
            assert actual == decision[stage + "_sha256"]
        assert tr["candidate_sha256"] == decision["candidate_sha256"]
        validation = read("validation/" + name + ".json")
        assert digest(validation) == change["validation_sha256"]
        split = f"validation_round{round_index}"
        assert change["validation_split"] == split and validation["seed"] == seed + 8000 + round_index
        for side, checkpoint in (("parent", parent_hash), ("candidate", decision["candidate_sha256"])):
            samples = sample_ref(validation[side + "_ref"], split, checkpoint, validation["seed"])
            checked += check_score(banks[split], samples, validation[side])
        check_decision(validation["parent"], validation["candidate"], decision)
        assert decision["accepted"] is decision["eligible"] and decision["gate_enforced"] is True
        assert decision["selection_reason"] == decision["reasons"] and decision["parent_sha256"] == parent_hash
        assert decision["rollback_verified"] is (not decision["accepted"])
        expected_hash = decision["candidate_sha256"] if decision["accepted"] else parent_hash
        expected_name = name if decision["accepted"] else parent_name
        assert decision["selected_sha256"] == expected_hash and change["selected_checkpoint"] == expected_name
        state[(seed, arm)] = (expected_hash, expected_name)
        selected[str(seed)][arm][str(round_index)] = expected_name
        checked += check_score(banks["final"], sample_ref(refs[name], "final", decision["candidate_sha256"], seed + 7000), result["scores"][name])
        check_decision(result["scores"][parent_name], result["scores"][name], result["candidate_final_effects"][name])
        assert change["training_cost"]["training_steps"] == len(step_events)
        assert change["training_cost"]["supervised_tokens"] == sum(e["supervised_tokens"] for e in step_events)
        assert change["training_cost"]["oracle_string_executions"] == len(pool) * (config["visible_examples"] + config["hidden_examples"])
    assert selected == result["selected"] == closed["payload"]["selected"] and closed["payload"]["changes"] == len(expected_changes)
    p64 = lambda name: result["scores"][name]["pass_at_k"]["64"]
    per_seed = [{"seed": s, "frontier_round2": p64(selected[str(s)]["corrected_frontier"]["2"]),
                 "frontier_round1": p64(selected[str(s)]["corrected_frontier"]["1"]),
                 "selected_round2": p64(selected[str(s)]["corrected_selected"]["2"]),
                 "initial": p64(f"s{s}_initial"), "base": p64(f"s{s}_base")} for s in config["training_seeds"]]
    avg = lambda key: sum(x[key] for x in per_seed) / len(per_seed)
    delta = avg("frontier_round2") - avg("selected_round2")
    positive = sum(x["frontier_round2"] > x["selected_round2"] for x in per_seed)
    criteria = {"positive_mean_primary_contrast": delta > 0, "positive_in_two_seeds": positive >= 2,
                "above_frozen_bootstrap": avg("frontier_round2") > avg("initial"), "above_unadapted_base": avg("frontier_round2") > avg("base"),
                "round_two_retains_round_one_mean": avg("frontier_round2") >= avg("frontier_round1")}
    assert result["screen"]["criteria"] == criteria and result["screen"]["passed"] is all(criteria.values())
    assert result["screen"]["primary_delta"] == delta and result["screen"]["positive_seeds"] == positive and result["screen"]["per_seed"] == per_seed
    for key in result["compute"]:
        expected_cost = sum(p["cost"][key] for p in sample_files.values()) + sum(r["training_cost"][key] for r in result["changes"])
        assert math.isclose(result["compute"][key], expected_cost, abs_tol=1e-6), key
    assert result["measurement_cost"]["program_checks"] == checked
    assert result["measurement_cost"]["string_check_upper_bound"] == checked * (config["visible_examples"] + config["hidden_examples"])
    assert events[-1]["payload"] == {"results_sha256": digest(result)}
    report = {"status": "passed", "artifacts_hashed": len(artifacts), "journal_events": count,
              "fresh_tasks_regenerated": sum(config["bank_counts"].values()), "harvest_searches_reexecuted": len(raw),
              "raw_samples_regraded": checked, "unique_sample_files": len(sample_files),
              "training_pool_rows_reverified": training_rows, "optimizer_steps_reconciled": steps_checked,
              "checkpoint_decisions_reconciled": len(expected_changes),
              "token_accounting": "Raw completion IDs decoded and counted; prompt and supervised tokens reconstructed with pinned tokenizer",
              "diversity_checks": "Canonical programs and visible outputs reconstructed with published interpreter",
              "limits": "Training and GPU sampling not reexecuted; shared generator/search and finite-example oracle. Hashes do not authenticate a hostile host. Timings are not independently reproduced."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Assertions must remain enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(parser.parse_args().run), indent=2))
