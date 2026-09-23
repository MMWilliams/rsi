"""Controlled retention experiment on frozen verified search trajectories."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import shutil
import sys
import time
import traceback
from pathlib import Path

from .banks import create_banks, template
from .common import ROOT, Journal, digest, verify_journal, write_json
from .neural import LocalModel, adapter_hash
from .retention import coverage_decision, measure, resolve_update, verified_pool
from .evaluation import paired_bootstrap
from .run import log


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_artifacts(root):
    artifacts = {p.relative_to(root).as_posix(): {"sha256": file_hash(p), "bytes": p.stat().st_size}
                 for p in sorted(root.rglob("*")) if p.is_file() and p.name not in ("artifact_manifest.json", "audit.json")}
    write_json(root / "artifact_manifest.json", artifacts)
    return artifacts


def make_report(result, root):
    lines = ["# Retention ablation", "", "Completed diagnostic; this experiment does not establish RSI.", "",
             "Frozen search trajectories isolate training-data retention and promotion policy. Final scores were deferred until all decisions were recorded.", "",
             "| Checkpoint | pass@1 | pass@8 | pass@64 | Distinct parseable programs / task |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for name, score in result["scores"].items():
        p = score["pass_at_k"]
        lines.append(f"| {name} | {p['1']:.1%} | {p['8']:.1%} | {p['64']:.1%} | {score['mean_distinct_parseable_programs']:.2f} |")
    lines += ["", "## Every update", "", "| Change | Pool rows | Gate eligible | Selected | Validation lost / gained | Selection reason |",
              "| --- | ---: | --- | --- | --- | --- |"]
    for row in result["changes"]:
        d = row["decision"]
        lines.append(f"| {row['change_id']} | {row['training']['rows']} | {d['eligible']} | {d['accepted']} | {len(d['lost_task_ids'])} / {len(d['gained_task_ids'])} | {', '.join(d['selection_reason'])} |")
    lines += ["", "## Paired final comparisons", ""]
    for label, value in result["comparisons"].items():
        lines.append(f"- {label}: {value['mean']:+.1%}; descriptive paired-task 95% bootstrap [{value['ci95'][0]:+.1%}, {value['ci95'][1]:+.1%}].")
    lines += ["", "One neural seed and 24 final tasks. Bootstrap intervals cover sampled tasks, not training-seed uncertainty. No parameter or training-seed selection from final results. Optimizer steps and nominal evaluation sample budgets are matched; tokens and wall time can differ. Syntactic diversity and visible-output signatures are diagnostics, not semantic capability proofs. The gate can reject useful changes and accept changes that regress elsewhere. Frozen harvest does not test a complete recursive loop.", "",
              "Full parent/candidate/selected hashes, row pools, per-step sample indices and losses, validation raw outputs, final raw outputs, compute deltas, and source snapshots are archived alongside this report."]
    (root / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/retention-v3.json")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    root = ROOT / "runs" / args.run_id
    root.mkdir(parents=True, exist_ok=False)
    journal = Journal(root / "events.jsonl")
    started = time.perf_counter()
    try:
        source = ROOT / config["source_run"]
        verify_journal(source / "events.jsonl")
        old_banks = json.loads((source / "protected_banks.json").read_text(encoding="utf-8"))
        old_meta = json.loads((source / "bank_manifest.json").read_text(encoding="utf-8"))
        if any(digest(rows) != old_meta[name]["sha256"] for name, rows in old_banks.items()):
            raise ValueError("Source task-bank manifest mismatch")
        # Exclude templates from every earlier local bank, including failed experiments.
        exclusions, origins = set(), {}
        for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
            previous = json.loads(path.read_text(encoding="utf-8"))
            exclusions.update(template(task["reference"]) for rows in previous.values() for task in rows)
            origins[str(path.relative_to(ROOT))] = file_hash(path)
        banks, metadata = create_banks(config, excluded_templates=exclusions)
        banks["train"] = old_banks["train"]
        metadata["train"] = {"count": len(banks["train"]), "sha256": digest(banks["train"]), "source": config["source_run"]}
        task_map = {task["id"]: task for task in banks["train"]}
        write_json(root / "config.json", config)
        write_json(root / "protected_banks.json", banks)
        write_json(root / "bank_manifest.json", metadata)
        write_json(root / "prior_bank_exclusions.json", {"source_hashes": origins, "templates": sorted(exclusions)})
        sources = list((ROOT / "rsi").glob("*.py")) + [ROOT / config["protocol"], ROOT / "requirements.lock.txt",
                   ROOT / "research-retention-2026-09-16.md", ROOT / "audit_retention.py"]
        sources += [ROOT / "vendor" / "trapdoor-loom" / name for name in ("dsl.py", "parse.py", "trapdoor.py")]
        for path in sources:
            dest = root / "source" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        source_hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sources}
        manifest = {"schema_version": 3, "run_id": args.run_id, "config_sha256": digest(config),
                    "python": sys.version, "platform": platform.platform(), "source_sha256": source_hashes,
                    "source_run": config["source_run"], "source_journal_sha256": file_hash(source / "events.jsonl")}
        write_json(root / "manifest.json", manifest)
        journal.append("preregistration", {"manifest": manifest, "config": config, "bank_manifest": metadata})
        groups = []
        for name in ("common_bootstrap", "search_round1", "search_round2"):
            source_rows = source / "verified_trajectories" / (name + ".json")
            rows = verified_pool([json.loads(source_rows.read_text(encoding="utf-8"))], task_map)
            groups.append(rows)
            write_json(root / "verified_trajectories" / (name + ".json"), rows)
            journal.append("input_trajectory_provenance", {"name": name, "source_sha256": file_hash(source_rows), "rows_sha256": digest(rows), "rows": len(rows)})
        from safetensors.torch import load_file
        checkpoint = source / "adapters" / "common_bootstrap" / "bootstrap" / "adapter_model.safetensors"
        model = LocalModel(config, journal)
        initial = load_file(str(checkpoint))
        model.restore("bootstrap", initial)
        model.copy_bootstrap()
        model.save_adapter("bootstrap", root / "adapters" / "initial")
        journal.append("initial_checkpoint", {"source": str(checkpoint), "file_sha256": file_hash(checkpoint), "tensor_sha256": adapter_hash(initial)})
        import torch
        journal.append("runtime", {"torch": torch.__version__, "cuda": torch.version.cuda,
                                   "gpu": torch.cuda.get_device_name(config["device"]), "seed": config["neural_seed"]})
        final_samples, selected, changes = {}, {}, []
        measurement_cost = {"program_checks": 0, "string_check_upper_bound": 0}
        def measured(tasks, samples):
            measurement_cost["program_checks"] += sum(len(samples[t["id"]]) for t in tasks)
            measurement_cost["string_check_upper_bound"] += sum(len(samples[t["id"]]) * (len(t["visible"]) + len(t["hidden"])) for t in tasks)
            return measure(tasks, samples, config["pass_k"])
        final_seed = config["neural_seed"] + 7000
        model.activate("bootstrap")
        log("Sampling initial final holdout; scores deferred")
        final_samples["initial"] = model.sample(banks["final"], config["samples_per_final_task"], final_seed)
        write_json(root / "final_samples" / "initial.json", final_samples["initial"])
        arms = [("fresh", "search", False, False), ("replay", "selftrain", True, False), ("replay_gated", "fixed_search", True, True)]
        for arm, adapter, replay, gate in arms:
            selected[arm] = "initial"
            for round_index in (1, 2):
                change_id = f"{arm}_round{round_index}"
                log(f"{change_id}: paired validation, training, and promotion")
                before = dict(model.ledger)
                validation = banks[f"validation_round{round_index}"]
                validation_seed = config["neural_seed"] + 8000 + round_index
                model.activate(adapter)
                parent = model.snapshot(adapter)
                parent_samples = model.sample(validation, config["validation_samples"], validation_seed)
                parent_score = measured(validation, parent_samples)
                pool = verified_pool(groups[:round_index + 1] if replay else [groups[round_index]], task_map)
                write_json(root / "training_pools" / (change_id + ".json"), pool)
                proposal = {"change_id": change_id, "intervention": "cumulative_verified_replay" if replay else "fresh_round_only",
                            "hypothesis": "Retaining earlier verified trajectories reduces loss of sampled coverage",
                            "gate_enforced": gate, "parent_sha256": adapter_hash(parent), "pool_sha256": digest(pool),
                            "comparison": "fresh versus replay isolates data retention; replay versus replay_gated isolates selection",
                            "validation_split": f"validation_round{round_index}", "parent_checkpoint": selected[arm], "final_feedback_used": False}
                journal.append("change_proposed", proposal)
                training = model.distill(pool, task_map, adapter, root / "adapters" / (change_id + "_candidate"), config["neural_seed"] + round_index)
                candidate_samples = model.sample(validation, config["validation_samples"], validation_seed)
                candidate_score = measured(validation, candidate_samples)
                decision = coverage_decision(parent_score, candidate_score)
                validation_record = {"parent_samples": parent_samples, "candidate_samples": candidate_samples,
                                     "parent": parent_score, "candidate": candidate_score, "seed": validation_seed}
                write_json(root / "validation" / (change_id + ".json"), validation_record)
                # Candidate final outputs are archived, but scores cannot influence promotion.
                final_samples[change_id] = model.sample(banks["final"], config["samples_per_final_task"], final_seed)
                write_json(root / "final_samples" / (change_id + ".json"), final_samples[change_id])
                decision = resolve_update(model, adapter, parent, decision, gate)
                if decision["accepted"]:
                    selected[arm] = change_id
                model.save_adapter(adapter, root / "adapters" / (change_id + "_selected"))
                row = {**proposal, "training": training, "decision": decision, "selected_checkpoint": selected[arm],
                       "validation_sha256": digest(validation_record),
                       "compute": {key: model.ledger[key] - before[key] for key in before}}
                changes.append(row)
                write_json(root / "changes" / (change_id + ".json"), row)
                journal.append("change_resolved", row)
                write_json(root / "progress.json", {"last_change": change_id, "resolved": len(changes), "selected": selected})
                log(f"{change_id}: accepted={decision['accepted']}; validation lost={len(decision['lost_task_ids'])}, gained={len(decision['gained_task_ids'])}")
        journal.append("optimization_closed", {"selected": selected, "changes": len(changes)})
        log("All decisions closed; scoring final outputs")
        scores = {name: measured(banks["final"], samples) for name, samples in final_samples.items()}
        final_effects = {row["change_id"]: coverage_decision(scores[row["parent_checkpoint"]], scores[row["change_id"]]) for row in changes}
        for arm, checkpoint_name in selected.items():
            scores[arm + "_selected"] = scores[checkpoint_name]
        comparisons = {}
        for left, right in (("replay_selected", "fresh_selected"), ("replay_gated_selected", "replay_selected"),
                            ("replay_gated_selected", "initial")):
            comparisons[left + "_minus_" + right] = paired_bootstrap([r["pass_at_k"]["64"] for r in scores[left]["tasks"]],
                                                                     [r["pass_at_k"]["64"] for r in scores[right]["tasks"]])
        if any(file_hash(ROOT / name) != expected for name, expected in source_hashes.items()):
            raise RuntimeError("Source changed during experiment")
        result = {"run_id": args.run_id, "status": "completed", "scores": scores, "changes": changes,
                  "selected": selected, "comparisons": comparisons, "compute": model.ledger,
                  "measurement_cost": measurement_cost, "candidate_final_effects": final_effects,
                  "wall_seconds": time.perf_counter() - started,
                  "limitations": ["one neural seed", "24 final tasks", "frozen harvest diagnostic", "not total-compute matched", "finite validation gate"]}
        write_json(root / "results.json", result)
        make_report(result, root)
        journal.append("completed", {"results_sha256": digest(result)})
        verify_journal(journal.path)
        seal_artifacts(root)
        write_json(ROOT / "runs" / "latest-retention.json", {"run_id": args.run_id, "report": str(root / "REPORT.md")})
        log(f"Completed: {root / 'REPORT.md'}")
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        journal.append("failed", failure)
        write_json(root / "FAILED.json", failure)
        raise


if __name__ == "__main__":
    main()
