"""Retrospective v2 failure analysis; never used as final v3 fitness."""
import json
from rsi.common import ROOT, write_json
from rsi.retention import measure, coverage_decision


def main():
    source = ROOT / "runs/pilot-20260916-v2-complete"
    banks = json.loads((source / "protected_banks.json").read_text(encoding="utf-8"))
    old = json.loads((source / "neural_results.json").read_text(encoding="utf-8"))
    by_id = {task["id"]: task for task in banks["final"]}
    scores = {}
    for name in ("base", "search_round1", "search_round2", "selftrain_round2", "fixed_search_round2"):
        tasks = [by_id[row["id"]] for row in old["scores"][name]["tasks"]]
        samples = json.loads((source / "neural_samples" / (name + ".json")).read_text(encoding="utf-8"))
        scores[name] = measure(tasks, samples, [1, 4, 8, 16, 32, 64])
        assert scores[name]["pass_at_k"] == old["scores"][name]["pass_at_k"]
    transitions = {a + "_to_" + b: coverage_decision(scores[a], scores[b])
                   for a, b in (("base", "search_round1"), ("search_round1", "search_round2"), ("base", "search_round2"))}
    value = {"source_run": str(source), "analysis_type": "retrospective_diagnostic", "scores": scores,
             "transitions": transitions, "observed": "Syntactic diversity decreased; second search round lost solved tasks without gains",
             "unproven_mechanism": "Fresh-only supervised training may overfit or forget; need controlled retention intervention",
             "caveat": "Syntax is not correctness; visible behavior is not universal semantics; finite samples cannot establish zero support"}
    write_json(ROOT / "analysis/v2-distillation-diagnosis.json", value)
    print(json.dumps({name: {"pass64": s["pass_at_k"]["64"], "distinct": s["mean_distinct_parseable_programs"],
                            "parseable": s["parseable_fraction"]} for name, s in scores.items()}, indent=2))


if __name__ == "__main__":
    main()
