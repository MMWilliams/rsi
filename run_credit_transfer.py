"""Run V12: matched transfer of inherited edit-credit tables."""
from __future__ import annotations

import argparse
import datetime
import json
import platform
import shutil
import sys
import time
import traceback
from pathlib import Path

from credit_transfer import scrambled_paired_table, table_from_v10
from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, digest, verify_journal, write_json
from rsi.evaluation import Evaluator, Worker, paired_bootstrap
from rsi.evolution import evolve
from rsi.operators import initial_catalog
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG


def _protected_exclusions():
    hashes, templates = {}, set()
    paths = sorted(list((ROOT / "runs").glob("*/protected_banks.json")) +
                   list((ROOT / "analysis").glob("**/protected_banks.json")))
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        hashes[rel] = file_hash(path)
        banks = json.loads(path.read_text(encoding="utf-8"))
        for rows in banks.values():
            templates.update(template(task["reference"]) for task in rows)
    return hashes, sorted(templates)


def run(config, root: Path):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    journal = Journal(root / "events.jsonl")
    started = time.perf_counter()
    worker = None
    try:
        protocol = ROOT / config["protocol"]
        source_evidence = ROOT / config["source_evidence"]
        source_audit = ROOT / config["source_evidence_audit"]
        evidence = json.loads(source_evidence.read_text(encoding="utf-8"))
        evidence_audit = json.loads(source_audit.read_text(encoding="utf-8"))
        if evidence.get("status") != "completed" or evidence_audit.get("status") != "passed":
            raise ValueError("V10 source evidence is not a completed, passed audit")
        pairs = evidence["pairs"]
        prior_hashes, excluded = _protected_exclusions()
        source_names = [config["protocol"], "credit_transfer.py", "run_credit_transfer.py",
                        "audit_credit_transfer.py", "requirements.lock.txt"]
        source_paths = list((ROOT / "rsi").glob("*.py")) + [ROOT / name for name in source_names]
        source_paths += [ROOT / "vendor/trapdoor-loom" / name for name in ("dsl.py", "parse.py", "trapdoor.py")]
        source_hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in source_paths}
        for path in source_paths:
            destination = root / "source" / path.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
        manifest = {"schema_version": 1, "run_id": root.name, "config_sha256": digest(config),
                    "source_sha256": source_hashes, "python": sys.version,
                    "platform": platform.platform(), "v10_results_sha256": file_hash(source_evidence),
                    "v10_audit_sha256": file_hash(source_audit)}
        write_json(root / "config.json", config)
        write_json(root / "manifest.json", manifest)
        write_json(root / "prior_bank_exclusions.json", {"source_hashes": prior_hashes, "templates": excluded})
        write_json(root / "common_macros.json", macros)
        write_json(root / "source_evidence.json", {"results": evidence, "audit": evidence_audit,
                                                     "results_sha256": file_hash(source_evidence),
                                                     "audit_sha256": file_hash(source_audit)})
        journal.append("preregistration", {"config": config, "manifest": manifest,
                       "prior_templates_sha256": digest(excluded), "source_evidence_sha256": file_hash(source_evidence)})

        bank_cfg = dict(config)
        banks, metadata = create_banks(bank_cfg, set(excluded))
        write_json(root / "protected_banks.json", banks)
        write_json(root / "bank_manifest.json", metadata)
        journal.append("banks_frozen", {"metadata": metadata, "sha256": digest(banks), "excluded_templates": len(excluded)})

        source_tables = {
            "immediate_only": table_from_v10(pairs, "immediate_only"),
            "observational_descendant": table_from_v10(pairs, "observational_descendant"),
            "paired_credit": table_from_v10(pairs, "paired_credit"),
            "scrambled_paired": scrambled_paired_table(pairs, config["bank_seed"] + 77000),
            "empty": {}, "random": {},
        }
        write_json(root / "initial_tables.json", source_tables)
        journal.append("source_tables_frozen", {"tables_sha256": digest(source_tables), "modes": list(source_tables)})

        worker = Worker()
        evaluator = Evaluator(journal, config, worker)
        conditions = config["conditions"]
        trajectories, transfer_scores = {}, {}
        for seed_index, seed in enumerate(config["seeds"]):
            dev = banks["development"][seed_index * config["transfer_group_tasks"]:(seed_index + 1) * config["transfer_group_tasks"]]
            adm = banks["admission"][seed_index * config["transfer_group_tasks"]:(seed_index + 1) * config["transfer_group_tasks"]]
            trajectories[str(seed)] = {}
            for condition in conditions:
                mode = "random" if condition == "random" else "adaptive"
                transfer_cfg = dict(config)
                if condition in ("immediate_only", "empty"):
                    transfer_cfg["credit_mode"] = "immediate_only"
                elif condition in ("observational_descendant",):
                    transfer_cfg["credit_mode"] = "observational_descendant"
                elif condition in ("paired_credit", "scrambled_paired"):
                    transfer_cfg["credit_mode"] = "paired_credit"
                transfer_banks = {"development": dev, "admission": adm}
                label = f"transfer/{condition}/s{seed}"
                journal.append("transfer_started", {"condition": condition, "seed": seed,
                               "initial_table_sha256": digest(source_tables[condition]),
                               "task_ids": [t["id"] for t in dev + adm]})
                trajectory = evolve(evaluator, transfer_banks, transfer_cfg, seed + 10000,
                                    mode=mode, initial_table=source_tables[condition],
                                    label=label, macros=macros)
                trajectories[str(seed)][condition] = trajectory
                journal.append("transfer_closed", {"condition": condition, "seed": seed,
                               "trajectory_sha256": digest(trajectory)})
            print(f"Transfer group {seed}: {len(conditions)} conditions closed", flush=True)

        journal.append("optimization_closed", {"groups": len(config["seeds"]), "conditions": conditions,
                        "trajectories_sha256": digest(trajectories)})
        ancestor = evaluator.evaluate(banks["final"], dict(BASE_CONFIG), "final/ancestor", macros=macros)
        final = {"ancestor": ancestor}
        for seed in config["seeds"]:
            for condition in conditions:
                state = trajectories[str(seed)][condition]["config"]
                label = f"final/{condition}/s{seed}"
                final[label] = evaluator.evaluate(banks["final"], state, label, macros=macros)
        scores = {label: {"correct": row["correct"], "n": row["n"], "accuracy": row["accuracy"],
                          "task_scores": [int(r["oracle_correct"]) for r in row["results"]]}
                  for label, row in final.items()}
        contrasts = {}
        base_scores = [final[f"final/immediate_only/s{seed}"]["results"] for seed in config["seeds"]]
        for condition in conditions:
            if condition == "immediate_only":
                continue
            left, right = [], []
            for seed in config["seeds"]:
                lhs = final[f"final/{condition}/s{seed}"]["results"]
                rhs = final[f"final/immediate_only/s{seed}"]["results"]
                left.extend(int(a["oracle_correct"]) for a in lhs)
                right.extend(int(b["oracle_correct"]) for b in rhs)
            contrasts[condition] = paired_bootstrap(left, right, seed=config["bank_seed"] + len(condition))
        result = {"status": "completed", "scores": scores, "contrasts_vs_immediate": contrasts,
                  "trajectories": trajectories, "ancestor": scores["ancestor"],
                  "cost": evaluator.ledger, "elapsed_seconds": time.perf_counter() - started,
                  "engineering_screen": {"positive_mean": {k: v["mean"] > 0 for k, v in contrasts.items()},
                                         "scope": "matched transfer component; no RSI claim"}}
        write_json(root / "evaluations.json", final)
        write_json(root / "trajectories.json", trajectories)
        write_json(root / "results.json", result)
        if any(file_hash(p) != h for p, h in [(ROOT / n, v) for n, v in source_hashes.items()]):
            raise RuntimeError("Source changed during transfer")
        journal.append("completed", {"results_sha256": digest(result)})
        seal_artifacts(root)
        return result
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(),
                   "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        journal.append("failed", failure)
        write_json(root / "FAILED.json", failure)
        raise
    finally:
        if worker is not None:
            worker.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--config", default="configs/credit-transfer-v12.json")
    args = parser.parse_args()
    cfg = json.loads((ROOT / args.config).read_text(encoding="utf-8"))
    print(json.dumps(run(cfg, ROOT / args.output), indent=2))
