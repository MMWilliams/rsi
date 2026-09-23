"""Render a single recorded edit's rationale and outcomes without evaluating it again."""
import argparse
import hashlib
import json
from pathlib import Path

from rsi.common import verify_journal


def explain(root, change_id):
    root = Path(root)
    journal = root / "events.jsonl"
    verify_journal(journal)
    events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    proposals = [e for e in events if e["kind"] == "search_change_proposed" and e["payload"]["change_id"] == change_id]
    resolutions = [e for e in events if e["kind"] == "search_change_resolved" and e["payload"]["change_id"] == change_id]
    if len(proposals) != 1 or len(resolutions) != 1:
        raise ValueError("Expected exactly one proposal and one resolution for this change")
    p, r = proposals[0], resolutions[0]
    change = r["payload"]
    assert p["seq"] < r["seq"]
    assert all(change[key] == value for key, value in p["payload"].items())
    lines = [f"# {change_id}", "", f"Run: `{root.name}`",
             f"Explanation script SHA-256: `{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}`",
             f"Journal head at rendering: `{events[-1]['sha256']}`",
             f"Journal events: {p['seq']} (proposed), {r['seq']} (resolved).",
             f"Resolution hash: `{r['sha256']}`", "",
             "This explains the implemented decision and recorded measurements. It does not prove the mechanism of an improvement.",
             "", "## Proposed change", "", f"Hypothesis: {change['hypothesis']}",
             f"Operator: `{change['operator']['name']}`; origin: `{change['operator']['origin']}`.",
             "", "```json", json.dumps(change["operator"]["updates"], indent=2), "```", ""]
    selection = change.get("selection")
    if selection:
        lines += ["## Why it was selected", "", selection["reason"], "",
                  f"Effect-table hash: `{selection['table_sha256']}`",
                  f"RNG before/after: `{selection['rng_before_sha256']}` / `{selection['rng_after_sha256']}`", ""]
        if selection["scores"]:
            lines += ["| Operator | Beta draw | Mean gain | Descendant mean | Combined score | Chosen |",
                      "|---|---:|---:|---:|---:|---|"]
            for score in selection["scores"]:
                lines.append(f"| {score['name']} | {score['productivity_draw']:.6f} | {score['mean_gain']:.6f} | {score['descendant_mean']:.6f} | {score['score']:.6f} | {'yes' if score['name'] == selection['selected'] else ''} |")
        else:
            lines.append(f"Uniform random choice from {len(selection['available'])} available operators.")
        lines += ["", "Scores are selection heuristics, not calibrated probabilities of future improvement."]
    else:
        lines += ["## Why it was selected", "", "This archive predates selection traces. The outcome is recorded, but the draw/ranking explanation is unavailable."]
    lines += ["", "## Outcome", "", f"Accepted: **{change['accepted']}**. Reason: `{change['reason']}`.",
              f"Selected configuration hash: `{change['selected_config_sha256']}`."]
    if change["valid"]:
        differences = {key: {"before": value, "after": change["candidate_config"][key]}
                       for key, value in change["parent_config"].items() if value != change["candidate_config"][key]}
        lines += ["", "Configuration changes:", "```json", json.dumps(differences, indent=2), "```"]
    else:
        lines.append(f"Invalid edit: {change.get('detail', '')}")
    evaluations = [e for e in events if e["kind"] == "evaluation" and e["seq"] < r["seq"]]
    generation_label = change_id.rsplit("/p", 1)[0]
    for stage, parent_key, child_key in (("Development", "parent_evaluation_request_sha256", "candidate_evaluation_request_sha256"),
                                        ("Admission", "admission_parent_request_sha256", "admission_candidate_request_sha256")):
        if child_key not in change:
            lines += ["", f"{stage}: candidate not evaluated."]
            continue
        pair = []
        labels = ((generation_label + "/parent", change_id + "/" + change["operator"]["name"])
                  if stage == "Development" else (generation_label + "/guard_parent", generation_label + "/guard_candidate"))
        for key, label in zip((parent_key, child_key), labels):
            matching = [e for e in evaluations if e["payload"]["request_sha256"] == change[key] and e["payload"]["label"] == label]
            if len(matching) != 1:
                raise ValueError("Expected exactly one linked evaluation with the recorded request and trajectory label")
            pair.append(matching[0])
        parent, child = [e["payload"] for e in pair]
        old = {row["task_id"]: row["oracle_correct"] for row in parent["results"]}
        new = {row["task_id"]: row["oracle_correct"] for row in child["results"]}
        assert old.keys() == new.keys()
        wins = [task for task in old if new[task] and not old[task]]
        losses = [task for task in old if old[task] and not new[task]]
        lines += ["", f"### {stage}", "",
                  f"Parent {parent['correct']}/{parent['n']}; candidate {child['correct']}/{child['n']}. Wins: {len(wins)}; losses: {len(losses)}.",
                  f"Evaluation events: {pair[0]['seq']} and {pair[1]['seq']}; matched by both request hash and trajectory label.",
                  f"Gained task IDs: {', '.join(wins) or 'none'}.", f"Lost task IDs: {', '.join(losses) or 'none'}.",
                  "", "Candidate evaluation cost record (logical counts; worker time excludes host grading):",
                  "```json", json.dumps(child.get("compute", {"note": "per-batch compute not recorded"}), indent=2), "```"]
    lines += ["", "## Statistics", "", "```json", json.dumps({"before": change["stats_before"], "after": change["stats_after"]}, indent=2), "```",
              "", "The complete-run audit separately checks these statistics and selection traces. A valid journal chain alone does not establish correctness."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("change_id")
    parser.add_argument("--output")
    args = parser.parse_args()
    text = explain(args.run, args.change_id)
    if args.output:
        path = Path(args.output).resolve()
        if path.is_relative_to(Path(args.run).resolve()):
            raise ValueError("Write explanations outside the sealed run archive")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(path)
    else:
        print(text)


if __name__ == "__main__":
    main()
