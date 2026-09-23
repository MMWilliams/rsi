"""Export an allowlisted public summary after independently auditing both source runs."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from rsi.common import ROOT, canonical, digest, verify_journal


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def point(label, score):
    rows = score["tasks"]
    if not rows or any(row["n"] != 64 for row in rows):
        raise ValueError("Public pass@64 summary requires 64 raw samples for every task")
    solved = sum(row["correct"] > 0 for row in rows)
    if abs(score["pass_at_k"]["64"] - solved / len(rows)) > 1e-12:
        raise ValueError("Stored pass@64 disagrees with task outcomes")
    return {"label": label, "solved_tasks": solved, "tasks": len(rows), "samples_per_task": 64}


def provenance(root):
    verify_journal(root / "events.jsonl")
    last = json.loads((root / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    if last["kind"] != "completed":
        raise ValueError("Only completed runs may be published")
    return {"run_id": root.name, "journal_head_sha256": last["sha256"],
            "files_sha256": {name: sha(root / name) for name in ("results.json", "audit.json", "manifest.json", "bank_manifest.json")}}


def build():
    v2 = ROOT / "runs/pilot-20260916-v2-complete"
    v3 = ROOT / "runs/retention-20260916-v3"
    results2, results3 = read(v2 / "results.json"), read(v3 / "results.json")
    audit2, audit3 = read(v2 / "audit.json"), read(v3 / "audit.json")
    if audit3.get("status") != "passed" or audit2.get("pass_at_k_reconciliation") != "passed":
        raise ValueError("Independent audits must pass before exporting")
    scores2, scores3 = results2["neural"]["scores"], results3["scores"]
    payload = {
        "schema_version": 1, "as_of": "2026-09-16", "rsi_demonstrated": False,
        "mission": "Develop trustworthy recursive self-improvement for research, cybersecurity, social good and policy, measured independently.",
        "application_directions": [
            {"id": "research", "title": "Research", "aim": "Improve how systems form hypotheses, run experiments and learn from failed results.", "measure": "Reproducible discoveries and stronger subsequent improvers at matched compute.", "status": "research_direction"},
            {"id": "cybersecurity", "title": "Cybersecurity", "aim": "Improve defensive analysis, vulnerability verification and remediation in authorized environments.", "measure": "Reproduced findings, validated fixes and false-positive rates on held-out systems.", "status": "research_direction"},
            {"id": "social-good", "title": "Social good", "aim": "Apply improving systems to public-interest problems, with outcomes defined alongside affected communities.", "measure": "Useful outcomes, access and error rates across the people and settings served.", "status": "research_direction"},
            {"id": "policy", "title": "Policy", "aim": "Support evidence synthesis, policy comparison and evaluation with traceable sources and explicit uncertainty.", "measure": "Source fidelity, reproducibility and independently reviewed decision-support quality.", "status": "research_direction"}],
        "status": "Research active; RSI not demonstrated",
        "scope": "Completed local research pilots; not a capability of the downloadable LEDGER release or the planning demo.",
        "metric": "Raw pass@64: tasks with at least one independently scored correct program among 64 samples. No search-based selection at evaluation.",
        "studies": [
            {"id": v2.name, "title": "Search, distillation and inherited edit statistics", "status": "completed_pilot",
             "model": "Qwen3-0.6B", "checkpoints": [point(label, scores2[key]) for label, key in
                 (("Initial shared bootstrap", "base"), ("Search + distillation: round 1", "search_round1"), ("Search + distillation: round 2", "search_round2"))],
             "finding": "Coverage rose, then regressed below the initial model. Inherited edit statistics did not beat the empty and scrambled controls.",
             "limitations": ["One neural training seed", "24 final neural tasks", "Bounded string-program domain", "Total compute not matched"],
             "audit": {"raw_samples_regraded": audit2["raw_samples_regraded_with_published_interpreter"], "training_rows_rechecked": audit2["verified_training_trajectories_rechecked"]},
             "provenance": provenance(v2)},
            {"id": v3.name, "title": "Verified replay and model promotion", "status": "completed_pilot", "model": "Qwen3-0.6B",
             "checkpoints": [point(label, scores3[key]) for label, key in
                 (("Initial shared bootstrap", "initial"), ("Fresh data only: final", "fresh_selected"), ("Cumulative replay: final", "replay_selected"), ("Replay + validation gate: final", "replay_gated_selected"))],
             "finding": "Replay retained more syntactic variety without sustained coverage gains. The validation gate accepted an update that lost two tasks on the separate final bank.",
             "limitations": ["One neural training seed", "24 final tasks; 12 validation tasks per round", "Frozen training harvest", "Different task bank from the first pilot; compare arms within each study", "Total compute not matched"],
             "audit": {"raw_samples_regraded": audit3["raw_samples_regraded_with_published_interpreter"], "training_rows_rechecked": audit3["training_pool_rows_reverified"]},
             "provenance": provenance(v3)}],
        "required_evidence": ["Sustained gains in raw large-k coverage across generations", "Later improvers produce larger gains from the same frozen ancestor", "Intact inheritance beats empty and scrambled controls", "Independent held-out evaluation and total-compute accounting"],
        "evidence_limits": "This public summary exposes measurements and archive hashes. Full raw archives remain local. Hashes are integrity references, not signatures or proof of universal correctness. Passing replay checks alone does not establish improvement.",
    }
    payload["snapshot_id"] = digest(payload)
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify existing copies without writing")
    args = parser.parse_args()
    for script, run in (("audit_results.py", "pilot-20260916-v2-complete"), ("audit_retention.py", "retention-20260916-v3")):
        subprocess.run([sys.executable, str(ROOT / script), str(ROOT / "runs" / run)], check=True, cwd=ROOT, capture_output=True)
    payload = build()
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"
    destinations = [ROOT / "exports/kyberos-rsi-status.json", ROOT.parents[1] / "kyberos/src/research/rsiEvidence.json",
                    ROOT.parents[1] / "kyberos/public/research/rsi/status.json", ROOT.parents[1] / "kyberos-backend/app/research/rsi_status.json"]
    for path in destinations:
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != data:
                raise ValueError(f"Evidence copy drift: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data, encoding="utf-8")
    print(f"{'Verified' if args.check else 'Exported'} {len(destinations)} identical copies; snapshot {payload['snapshot_id']}")


if __name__ == "__main__":
    main()
