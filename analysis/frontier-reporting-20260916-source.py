"""Render an audited v9 study and per-change evidence without selecting checkpoints."""
import argparse
import datetime
import json
import time
from pathlib import Path

from audit_frontier_distillation import audit as audit_run
from rsi.common import write_json
from rsi.retention_run import file_hash


def evidence_snapshot(root):
    """Bind a local report to exact archive bytes; this is not authentication."""
    manifest = json.loads((root / "artifact_manifest.json").read_text())
    snapshot = {"artifact_manifest.json": file_hash(root / "artifact_manifest.json")}
    for name, expected in manifest.items():
        path = (root / name).resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError(f"Invalid evidence path: {name}")
        actual = file_hash(path)
        if actual != expected["sha256"] or path.stat().st_size != expected["bytes"]:
            raise ValueError(f"Evidence changed: {name}")
        snapshot[name] = actual
    return snapshot


def summarize(root, output):
    if not __debug__:
        raise RuntimeError("The independent auditor requires assertions enabled")
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or root in output.parents:
        raise ValueError("Write the report outside the sealed run archive")
    if output.exists() or output.with_suffix(".json").exists():
        raise FileExistsError(output)
    read = lambda name: json.loads((root / name).read_text())
    if (root / "FAILED.json").exists() or read("results.json").get("status") != "completed":
        raise ValueError("Only a completed, nonfailed study can produce this report")
    before = evidence_snapshot(root)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    wall, cpu = time.perf_counter(), time.process_time()
    audit = audit_run(root)
    audit_seconds, audit_cpu = time.perf_counter() - wall, time.process_time() - cpu
    if audit.get("status") != "passed" or evidence_snapshot(root) != before:
        raise ValueError("Evidence did not pass a stable, fresh independent audit")
    receipt = {"started_utc": started, "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "audit_seconds": audit_seconds, "audit_process_seconds": audit_cpu,
               "audit_sha256": file_hash(root / "audit.json"),
               "artifact_manifest_sha256": before["artifact_manifest.json"],
               "auditor_source_sha256": file_hash(Path(__file__).with_name("audit_frontier_distillation.py")),
               "method": "Fresh independent audit, then archive hashes rechecked before report publication",
               "limits": "Host-owned provenance; not authentication against a hostile host"}
    result, config = read("results.json"), read("config.json")
    interpretation = {
        "measurement_target": "Observed raw neural pass@k on this frozen final bank, averaged across the configured seeds",
        "sampling_unit": "Task within checkpoint within training seed; the same tasks recur across arms and seeds",
        "randomness": "Each training seed also determines an evaluation seed; seed variation mixes training and generation randomness",
        "uncertainty": "Per-seed contrasts are descriptive; no confidence interval or population-level significance claim is made",
        "decision_scope": "The preregistered advancement screen is an engineering decision, not proof of RSI",
        "mechanism_scope": "Controls compare complete training pipelines; weight-level causes and transfer to other domains are not identified",
        "mission_scope": "Research, cybersecurity, social good and policy remain intended applications with separate outcome evaluations outstanding",
    }
    scores, selected = result["scores"], result["selected"]
    get = lambda checkpoint, k: scores[checkpoint]["pass_at_k"][str(k)]
    means = {}
    for arm in config["arms"]:
        means[arm] = {}
        for round_index in (1, 2):
            keys = [selected[str(s)][arm][str(round_index)] for s in config["training_seeds"]]
            means[arm][str(round_index)] = {str(k): sum(get(key, k) for key in keys) / len(keys) for k in config["pass_k"]}
    lines = ["# Verified-frontier distillation: audited results", "",
             f"Run: `{root.name}`. Engineering screen: **{'passed' if result['screen']['passed'] else 'failed'}**. RSI remains unproved.", "",
             f"{len(config['arms'])} harvest controls, {len(config['training_seeds'])} training seeds, {config['rounds']} rounds; common bootstrap and task-balanced anchor/cumulative replay. Final scores were deferred until decisions closed.", "",
             "## Selected checkpoints", "", "Means across configured training/evaluation seeds on the same final task bank.", "",
             "| Condition | Initial pass@64 | Selected round 1 | Selected round 2 | Final pass@1 |",
             "| --- | ---: | ---: | ---: | ---: |"]
    initial = sum(get(f"s{s}_initial", 64) for s in config["training_seeds"]) / len(config["training_seeds"])
    base = sum(get(f"s{s}_base", 64) for s in config["training_seeds"]) / len(config["training_seeds"])
    for arm in config["arms"]:
        lines.append(f"| {arm} | {initial:.2%} | {means[arm]['1']['64']:.2%} | {means[arm]['2']['64']:.2%} | {means[arm]['2']['1']:.2%} |")
    lines += ["", f"Unadapted base mean pass@64: {base:.2%}. Frozen bootstrap: {initial:.2%}.", "",
              "## Measurement scope", ""]
    for value in interpretation.values():
        lines.append("- " + value + ".")
    lines += ["", "## Raw pass@k curves", "",
              "Mean selected round-two checkpoints; every declared k is shown. These columns reuse the same samples and are not independent tests.", "",
              "| Condition | " + " | ".join(f"pass@{k}" for k in config["pass_k"]) + " |",
              "| --- | " + " | ".join("---:" for _ in config["pass_k"]) + " |"]
    for label in ("base", "initial"):
        values = [sum(get(f"s{s}_{label}", k) for s in config["training_seeds"]) / len(config["training_seeds"]) for k in config["pass_k"]]
        lines.append("| " + label + " | " + " | ".join(f"{value:.2%}" for value in values) + " |")
    for arm in config["arms"]:
        lines.append("| " + arm + " | " + " | ".join(f"{means[arm]['2'][str(k)]:.2%}" for k in config["pass_k"]) + " |")
    lines += ["",
              "## Preregistered screen", ""]
    for name, passed in result["screen"]["criteria"].items():
        lines.append(f"- {name}: {'passed' if passed else 'failed'}.")
    lines += ["", "## Every checkpoint decision", "",
              "Final effects compare the candidate with its actual parent; they did not influence admission.", "",
              "| Change | Accepted | Admission gained / lost tasks | Final gained / lost tasks | Final pass@64 change | Admission reason |",
              "| --- | --- | ---: | ---: | ---: | --- |"]
    explanations = []
    for row in result["changes"]:
        name, decision = row["change_id"], row["decision"]
        effect = result["candidate_final_effects"][name]
        validation = read("validation/" + name + ".json")
        pool = read(f"training_pools/{row['arm']}_round{row['round']}.json")
        final_regression = bool(effect["lost_task_ids"]) or effect["pass_k_delta"] < -1e-12 or effect["pass1_delta"] < -1e-12
        disagreement = ("accepted_with_observed_final_regression" if decision["accepted"] and final_regression else
                        "rejected_despite_observed_final_eligibility" if not decision["accepted"] and effect["eligible"] else "no_observed_gate_disagreement")
        record = {"change_id": name, "arm": row["arm"], "seed": row["seed"], "round": row["round"],
                  "parent_checkpoint": row["parent_checkpoint"], "selected_checkpoint": row["selected_checkpoint"],
                  "parent_sha256": row["parent_sha256"], "candidate_sha256": decision["candidate_sha256"],
                  "selected_sha256": decision["selected_sha256"], "pool_sha256": row["pool_sha256"],
                  "rows_by_stratum": {s: sum(r["stratum"] == s for r in pool) for s in ("anchor", "harvest")},
                  "tasks_by_stratum": {s: len({r["task_id"] for r in pool if r["stratum"] == s}) for s in ("anchor", "harvest")},
                  "optimizer_steps": row["training"]["steps"], "training_cost": row["training_cost"],
                  "admission": decision, "final_effect": effect, "observed_gate_disagreement": disagreement,
                  "explanation_scope": {"admission_basis": "Recorded finite validation outcomes only",
                      "final_effect_basis": "Candidate versus its actual parent on deferred final samples",
                      "mechanism_status": "No weight-level causal mechanism identified; loss, gradients and target draws are observations",
                      "next_step": "Use predeclared arm contrasts; do not retrospectively promote a rejected checkpoint"},
                  "validation_sha256": row["validation_sha256"],
                  "sampling_refs": {side: validation[side + "_ref"] for side in ("parent", "candidate")}}
        explanations.append(record)
        lines.append(f"| {name} | {decision['accepted']} | {len(decision['gained_task_ids'])} / {len(decision['lost_task_ids'])} | {len(effect['gained_task_ids'])} / {len(effect['lost_task_ids'])} | {effect['pass_k_delta']:+.2%} | {', '.join(decision['selection_reason'])} |")
    contrasts = {}
    for a, b, meaning in (("corrected_selected", "baseline_selected", "filter effect in this training pipeline"),
                          ("corrected_first_verified", "corrected_selected", "additional solved training tasks"),
                          ("corrected_frontier", "corrected_first_verified", "multiple programs for the same training tasks")):
        contrasts[a + " minus " + b] = {"interpretation": meaning,
            "per_seed_pass64_delta": {str(s): get(selected[str(s)][a]['2'], 64) - get(selected[str(s)][b]['2'], 64) for s in config["training_seeds"]},
            "mean_pass64_delta": means[a]['2']['64'] - means[b]['2']['64']}
    lines += ["", "## Controlled training-pipeline contrasts", ""]
    for name, row in contrasts.items():
        lines.append(f"- {name}: {row['mean_pass64_delta']:+.2%} mean selected round-two pass@64; {row['interpretation']}. Seed deltas: {row['per_seed_pass64_delta']}.")
    lines += ["", "## Costs and limits", "",
              f"Runtime: {result['elapsed_seconds']:.2f} seconds. Generated tokens: {result['compute']['generated_tokens']:,}; supervised tokens: {result['compute']['supervised_tokens']:,}; optimizer steps: {result['compute']['training_steps']:,}.", "",
              "Full acquisition costs, exact-replay work, generated prompt/completion tokens, training draws and oracle checks are in results.json. Audit reexecution is additional verification work. Matched steps and examples do not match total compute or target-token counts.", "",
              f"Audit: {audit['artifacts_hashed']} artifacts, {audit['raw_samples_regraded']:,} sample regradings, {audit['optimizer_steps_reconciled']} optimizer steps and {audit['checkpoint_decisions_reconciled']} checkpoint decisions reconciled.", "",
              f"These are {len(config['training_seeds'])} training seeds sharing a bank and bootstrap, not independent task-bank replications. A finite gate can disagree with held-out outcomes. Syntactic variants need not be semantically distinct. Frozen harvest does not close the interleaved loop or prove improved improvers, inheritance, novel edit types or mission-domain benefit.", "",
              "Per-change JSON links the exact pools, sampling evidence, checkpoint hashes and observed outcomes. Admission/final disagreement labels describe this sample; they do not establish a true error rate or authorize retrospective checkpoint selection.", "",
              f"Report-time independent audit: {audit_seconds:.2f} wall seconds, {audit_cpu:.2f} process CPU seconds, additional to the experiment ledger. The JSON receipt binds the report to the exact artifact manifest and audit output."]
    if evidence_snapshot(root) != before or file_hash(root / "audit.json") != receipt["audit_sha256"]:
        raise ValueError("Evidence changed while rendering the report")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(output.with_suffix(".json"), {"run_id": root.name, "source_sha256": {n: file_hash(root / n) for n in ("results.json", "audit.json", "config.json")},
        "analysis_code_sha256": file_hash(Path(__file__)), "audit_receipt": receipt,
        "verified_evidence_sha256": before, "interpretation": interpretation,
        "means": means, "contrasts": contrasts, "changes": explanations,
        "observed_gate_disagreements": {key: sum(r["observed_gate_disagreement"] == key for r in explanations) for key in sorted({r["observed_gate_disagreement"] for r in explanations})}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("output")
    args = parser.parse_args()
    summarize(Path(args.run), Path(args.output))
