"""Render a v7 decision from sealed evidence, without a new search or score."""
import argparse
import hashlib
import json
from pathlib import Path

from rsi.common import verify_journal


def explain(root, label):
    root = Path(root).resolve()
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    for name in ("events.jsonl", "trajectories.json", "config.json"):
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == manifest[name]["sha256"], "Archive changed"
    count = verify_journal(root / "events.jsonl")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]

    def event(kind, name):
        matches = [e for e in events if e["kind"] == kind and e["payload"].get("label") == name]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {kind}: {name}")
        return matches[0]

    selection = event("fragment_proposals", label)
    resolution = event("fragment_change_resolved", label)
    memory_update = event("fragment_memory_updated", label)
    chosen = selection["payload"]
    decision = resolution["payload"]
    trajectory_label, generation = label.rsplit("/g", 1)
    trajectory = next(t["trajectory"] for t in read("trajectories.json") if t["trajectory"]["label"] == trajectory_label)
    memory = trajectory["snapshots"][generation]["memory"]
    parent = event("evaluation", label + "/parent")["payload"]
    admission = event("evaluation", label + "/guard_parent")["payload"]
    audit = read("audit.json") if (root / "audit.json").exists() else {"status": "not yet run"}
    lines = [f"# Library change: {label}", "", f"Run: `{root.name}`. Semantic audit: **{audit['status']}**.", "",
             "This explanation reads recorded evidence; it performs no new search and does not establish a causal mechanism.", "",
             "## Parent and proposal rule", "", f"Mode: `{chosen['mode']}`. Parent stored library entries: {len(chosen['parent_macros'])} (the historical four-atom entry is ignored by search).",
             f"Parent development score: {parent['correct']}/{parent['n']}; admission score: {admission['correct']}/{admission['n']}.", "",
             "Library candidates rank by visible compatibility, number of supporting solution certificates, fragment length, then lexical text. Numeric and frozen controls use their declared fixed proposals.",
             f"This generation added {len(memory_update['payload']['added'])} fragment-certificate links from verified harvest solutions.",
             f"Visible ranking charged {chosen['ranking_primitive_upper_bound']:,} primitive executions as an upper bound.", "",
             "## Candidate outcomes", "", "| Index | Kind | Development change | Admission change | Decision |", "| --- | --- | ---: | ---: | --- |"]
    for attempt in decision["attempts"]:
        admission_gain = "not evaluated" if attempt["admission_gain"] is None else f"{attempt['admission_gain'] * 100:+.3f} pp"
        lines.append(f"| {attempt['index']} | {attempt['proposal']['kind']} | {attempt['development_gain'] * 100:+.3f} pp | {admission_gain} | {attempt['reason']} |")
    lines += ["", "Only the development winner gets the admission test. Acceptance requires positive development gain and no net admission regression.", ""]
    for attempt in decision["attempts"]:
        index, proposal = attempt["index"], attempt["proposal"]
        measured = event("evaluation", label + f"/p{index}")["payload"]
        lines += [f"## Proposal {index}", "", f"`{proposal['name']}`", "",
                  f"Candidate score: {measured['correct']}/{measured['n']}. Accepted: **{attempt['accepted']}**.",
                  f"Development wins: {attempt['development_delta']['wins'] or 'none'}.",
                  f"Development losses: {attempt['development_delta']['losses'] or 'none'}."]
        if attempt["admission_delta"] is not None:
            lines += [f"Admission wins: {attempt['admission_delta']['wins'] or 'none'}.",
                      f"Admission losses: {attempt['admission_delta']['losses'] or 'none'}."]
        changes = {k: {"before": chosen["parent_config"][k], "after": v} for k, v in proposal["config"].items() if chosen["parent_config"][k] != v}
        lines += ["", "Parameter changes: `" + json.dumps(changes, sort_keys=True) + "`.",
                  f"Library additions: {sorted(set(proposal['macros']) - set(chosen['parent_macros'])) or 'none'}."]
        if proposal["kind"] == "add_fragment":
            rank = next(r for r in chosen["rankings"] if r["fragment"] == proposal["name"])
            evidence = memory[proposal["name"]]
            lines += [f"Visible-compatible tasks: {len(rank['compatible_tasks'])}; supporting certificates: {rank['support']}; atoms: {rank['atoms']}.",
                      f"Evidence records marked as scrambled: {sum('scrambled_from' in e for e in evidence)}/{len(evidence)}.", "",
                      "Source certificate links (request hash / task ID; full provenance is in the snapshot):", ""]
            for entry in evidence:
                lines.append(f"- `{entry['request_sha256']}` / `{entry['task_id']}`" + (" (scrambled composition control)" if "scrambled_from" in entry else ""))
        lines += ["", f"Candidate evaluation request: `{attempt['candidate_request_sha256']}`.",
                  f"Parent evaluation request: `{attempt['parent_request_sha256']}`.",
                  "Candidate logical charges, including replay: `" + json.dumps(measured["compute"], sort_keys=True) + "`.", ""]
    lines += ["## Provenance", "", f"Journal: {count} events; final hash `{events[-1]['sha256']}`.",
              f"Proposal event: {selection['seq']} / `{selection['sha256']}`.",
              f"Resolution event: {resolution['seq']} / `{resolution['sha256']}`.",
              f"Memory: `{chosen['memory_sha256']}`.",
              f"Explanation script: `{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}`.", "",
              "Finite admission examples can miss regressions. Hashes detect changes but do not authenticate the host. Artifact gains alone do not demonstrate a better improver or RSI."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("label")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    target, root = Path(args.output).resolve(), Path(args.run).resolve()
    if target == root or root in target.parents:
        raise ValueError("Explanation must remain outside the sealed archive")
    report = explain(root, args.label)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report, encoding="utf-8")
    print(target)
