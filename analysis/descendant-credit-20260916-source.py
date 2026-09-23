"""Measure historical credit and local score sensitivity; never simulate unseen edits."""
import argparse
from collections import Counter
import datetime
import json
import math
from pathlib import Path
import time

from audit_inheritance import audit
from rsi.retention_run import file_hash
from rsi.common import write_json


def score_sensitivity(trace):
    if trace["mode"] == "random":
        return {"mode": "random", "score_sensitivity": "not_applicable"}
    rows = trace["scores"]
    if not rows:
        raise ValueError("Adaptive trace has no alternatives")
    for row in rows:
        expected = row["productivity_draw"] + row["mean_gain"] + .25 * row["descendant_mean"]
        if not math.isclose(row["score"], expected, abs_tol=1e-12):
            raise ValueError("Recorded score arithmetic disagrees")
    pick = lambda fn: max(rows, key=lambda row: (fn(row), row["name"]))["name"]
    full = pick(lambda row: row["score"])
    if full != trace["selected"]:
        raise ValueError("Recorded selection disagrees")
    no_descendant = pick(lambda row: row["productivity_draw"] + row["mean_gain"])
    draw_only = pick(lambda row: row["productivity_draw"])
    return {"mode": trace["mode"], "selected": full, "without_descendant_term": no_descendant,
            "draw_only": draw_only, "descendant_term_flips_local_choice": full != no_descendant,
            "all_mean_terms_flip_local_choice": full != draw_only,
            "nonzero_descendant_terms": sum(row["descendant_mean"] != 0 for row in rows),
            "largest_absolute_descendant_term": max(abs(.25 * row["descendant_mean"]) for row in rows),
            "available": trace["available"], "rng_before_sha256": trace["rng_before_sha256"],
            "table_sha256": trace["table_sha256"]}


def reconstruct_credit(trajectory, initial):
    totals = {name: {"trials": row["descendant_trials"], "gain_sum": row["descendant_gain_sum"]}
              for name, row in initial.items()}
    lineage, records = [], []
    for decision in trajectory["decisions"]:
        gain = decision["admission_gain"]
        if gain is not None:
            multiplicity = Counter(row["operator"] for row in lineage)
            for ancestor in lineage:
                name = ancestor["operator"]
                totals[name]["trials"] += 1
                totals[name]["gain_sum"] += gain
                records.append({"ancestor_change_id": ancestor["change_id"], "operator": name,
                    "ancestor_generation": ancestor["generation"], "later_generation": decision["generation"],
                    "later_operator": decision["operator"], "later_admission_gain": gain,
                    "later_candidate_accepted": decision["accepted"],
                    "same_operator_occurrences_in_lineage": multiplicity[name]})
        if decision["accepted"]:
            accepted = [a for a in decision["attempts"] if a["accepted"]]
            if len(accepted) != 1:
                raise ValueError("Accepted generation needs exactly one accepted attempt")
            lineage.append({"operator": decision["operator"], "change_id": accepted[0]["change_id"],
                            "generation": decision["generation"]})
        snapshot = trajectory["snapshots"][str(decision["generation"])]["table"]
        for name, expected in totals.items():
            row = snapshot[name]
            if row["descendant_trials"] != expected["trials"] or not math.isclose(row["descendant_gain_sum"], expected["gain_sum"], abs_tol=1e-12):
                raise ValueError("Descendant credit reconstruction disagrees")
    return records


def summarize_group(rows):
    adaptive = [r for r in rows if r["mode"] != "random"]
    return {"recorded_choices": len(rows), "adaptive_choices": len(adaptive),
            "random_choices": len(rows) - len(adaptive),
            "choices_with_nonzero_descendant_terms": sum(r["nonzero_descendant_terms"] > 0 for r in adaptive),
            "descendant_term_local_choice_flips": sum(r["descendant_term_flips_local_choice"] for r in adaptive),
            "all_mean_terms_local_choice_flips": sum(r["all_mean_terms_flip_local_choice"] for r in adaptive),
            "largest_absolute_descendant_term": max((r["largest_absolute_descendant_term"] for r in adaptive), default=0)}


def analyze(root, output):
    if not __debug__:
        raise RuntimeError("Independent audit requires assertions")
    root, output = Path(root).resolve(), Path(output).resolve()
    if root in output.parents or output == root:
        raise ValueError("Analysis belongs outside the sealed archive")
    if output.exists() or output.with_suffix(".md").exists():
        raise FileExistsError(output)
    names = ["config.json", "source_trajectories.json", "transfer_trajectories.json", "artifact_manifest.json"]
    before = {name: file_hash(root / name) for name in names}
    started = time.perf_counter()
    audit_result = audit(root)
    audit_seconds = time.perf_counter() - started
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    sources, transfers = read(names[1]), read(names[2])
    choices, credits, source_tables = [], [], []
    for kind, source_seed, condition, trajectory in (
        [("source", t["seed"], "balanced", t) for t in sources] +
        [("transfer", t["source_seed"], t["condition"], t["trajectory"]) for t in transfers]
    ):
        initial = trajectory["snapshots"]["0"]["table"]
        for row in reconstruct_credit(trajectory, initial):
            credits.append({"kind": kind, "source_seed": source_seed, "condition": condition, **row})
        for decision in trajectory["decisions"]:
            for attempt in decision["attempts"]:
                choices.append({"kind": kind, "source_seed": source_seed, "condition": condition,
                    "generation": decision["generation"], "change_id": attempt["change_id"],
                    **score_sensitivity(attempt["selection"])})
        if kind == "source":
            source_tables.extend({"source_seed": source_seed, "operator": name, **stats}
                                 for name, stats in trajectory["table"].items())
    groups = {kind: summarize_group([r for r in choices if r["kind"] == kind]) for kind in ("source", "transfer")}
    for condition in sorted({r["condition"] for r in choices if r["kind"] == "transfer"}):
        groups["transfer/" + condition] = summarize_group([r for r in choices if r["kind"] == "transfer" and r["condition"] == condition])
    credit_summary = {}
    for kind in ("source", "transfer"):
        rows = [r for r in credits if r["kind"] == kind]
        credit_summary[kind] = {"credited_ancestor_occurrences": len(rows),
            "distinct_later_decisions": len({(r["source_seed"], r["condition"], r["later_generation"]) for r in rows}),
            "credits_from_rejected_later_candidates": sum(not r["later_candidate_accepted"] for r in rows),
            "credits_with_repeated_operator_name": sum(r["same_operator_occurrences_in_lineage"] > 1 for r in rows),
            "positive_credits": sum(r["later_admission_gain"] > 0 for r in rows),
            "zero_credits": sum(r["later_admission_gain"] == 0 for r in rows),
            "negative_credits": sum(r["later_admission_gain"] < 0 for r in rows)}
    result = {"run_id": root.name, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "analysis_code_sha256": file_hash(Path(__file__)), "inputs_sha256": before,
              "fresh_audit_sha256": file_hash(root / "audit.json"), "audit_seconds": audit_seconds,
              "audit_result": audit_result, "groups": groups, "credit_summary": credit_summary,
              "source_table_entries": len(source_tables),
              "source_entries_with_descendant_trials": sum(r["descendant_trials"] > 0 for r in source_tables),
              "source_entries_with_nonzero_descendant_sum": sum(r["descendant_gain_sum"] != 0 for r in source_tables),
              "choices": choices, "credit_events": credits, "source_final_tables": source_tables,
              "scope": "Historical local score sensitivity holding recorded draws, available actions and prior choices fixed; not a policy rollout or causal descendant effect",
              "no_new_evaluation": "No model inference, training, task generation or new oracle queries; independent audit regrades archived outcomes including old finals"}
    if {name: file_hash(root / name) for name in names} != before:
        raise ValueError("Inputs changed during analysis")
    lines = ["# Descendant credit: recorded signal and local decision influence", "",
             f"Archive `{root.name}`; independently re-audited. This is a retrospective diagnostic, not a new inheritance experiment.", "",
             "| Trace group | Adaptive choices | Nonzero descendant term available | Local choices flipped by descendant term |",
             "| --- | ---: | ---: | ---: |"]
    for label, row in groups.items():
        lines.append(f"| {label} | {row['adaptive_choices']} | {row['choices_with_nonzero_descendant_terms']} | {row['descendant_term_local_choice_flips']} |")
    lines += ["", f"Source tables: {result['source_entries_with_descendant_trials']}/{len(source_tables)} operator entries have descendant trials; {result['source_entries_with_nonzero_descendant_sum']} have a nonzero descendant gain sum.", "",
              "## What the statistic means", "",
              "Each accepted ancestor occurrence receives every subsequent selected candidate's admission gain, including rejected candidates. Multiple occurrences of one operator name receive repeated credit for the same later observation. These credits are dependent observations, not independent evidence or randomized attribution to an ancestor.", "",
              "Removing a term from a recorded score holds the beta draw, available actions and prior choices fixed. After a changed choice, subsequent states, exclusions, tables and random streams may diverge. Therefore local flips do not estimate an ablated policy's final performance. In source calibration all twelve edits were evaluated; a changed proposal ordering alone does not change that generation's candidate set.", "",
              "## Recorded credits", ""]
    for label, row in credit_summary.items():
        lines.append(f"- {label}: {row['credited_ancestor_occurrences']} ancestor credits from {row['distinct_later_decisions']} later decisions; {row['credits_from_rejected_later_candidates']} credits came from rejected candidates; {row['credits_with_repeated_operator_name']} involved repeated operator names.")
    lines += ["", "## Implication for the next improver test", "",
              "Separate immediate-effect inheritance from descendant-credit inheritance in prospective common-ancestor forks. Run descendants from paired states with and without the earlier edit to test its contribution, holding downstream policy and budgets fixed. Report rejection and measurement uncertainty. A coefficient change alone cannot establish useful descendant knowledge.", "",
              f"Independent audit cost: {audit_seconds:.2f} seconds. No live experiment source was changed. Full credit events, local sensitivities, hashes and audit results are in the adjacent JSON."]
    write_json(output, result)
    output.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"groups": groups, "credit_summary": credit_summary,
            "source_entries_with_descendant_trials": result["source_entries_with_descendant_trials"],
            "source_entries_with_nonzero_descendant_sum": result["source_entries_with_nonzero_descendant_sum"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(analyze(args.run, args.output), indent=2))
