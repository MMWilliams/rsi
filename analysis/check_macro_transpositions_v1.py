"""Instrument the frozen search on source requests; do not alter its choices."""
import argparse
import hashlib
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi import search
from rsi.common import digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("--limit", type=int, default=128)
    args = parser.parse_args()
    root = Path(args.run)
    original = inspect.getsource(search.solve)
    old = "            if next_atoms in seen:\n                continue\n            seen.add(next_atoms)"
    new = """            if next_atoms in seen:
                if cost + atom_cost < first_cost[next_atoms] - 1e-12:
                    discarded.append({"atoms": list(next_atoms), "first_cost": first_cost[next_atoms],
                                      "discarded_cost": cost + atom_cost, "macro_edge": item["macro"]})
                continue
            first_cost[next_atoms] = cost + atom_cost
            seen.add(next_atoms)"""
    assert original.count(old) == 1
    namespace = dict(vars(search))
    modified = original.replace("    seen = set()", "    seen = set()\n    first_cost = {}\n    discarded = []").replace(old, new)
    modified = modified.replace("    return payload", "    return payload, discarded")
    exec(compile(modified, "<instrumented-frozen-search>", "exec"), namespace)
    solve = namespace["solve"]
    checked, affected, examples = 0, 0, []
    with (root / "events.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event["kind"] != "evaluation":
                continue
            data = event["payload"]
            if not data["label"].startswith("source/library/") or not data["label"].endswith(("/p0", "/p1")):
                continue
            request = data["request"]
            for task, recorded in zip(request["tasks"], data["results"]):
                actual, discarded = solve(task, request["config"], request["budget"], request["max_atoms"], request["macros"], [])
                assert actual == {k: v for k, v in recorded.items() if k != "oracle_correct"}, "Instrumentation changed behavior"
                checked += 1
                if discarded:
                    affected += 1
                    if len(examples) < 10:
                        examples.append({"label": data["label"], "request_sha256": data["request_sha256"],
                                         "task": task, "config": request["config"], "budget": request["budget"],
                                         "max_atoms": request["max_atoms"], "macros": request["macros"],
                                         "recorded_result": actual, "discarded": discarded})
                if checked >= args.limit:
                    break
            if checked >= args.limit:
                break
    output = {"scope": "post hoc source candidate instrumentation; no changed search output, hidden example or final task used",
              "source_requests_checked": checked, "tasks_with_cheaper_discarded_route": affected, "examples": examples,
              "search_source_sha256": hashlib.sha256(inspect.getsourcefile(search.solve).encode()).hexdigest(),
              "search_file_sha256": hashlib.sha256(Path(inspect.getsourcefile(search.solve)).read_bytes()).hexdigest(),
              "instrumented_function_sha256": digest(modified),
              "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    target = Path(__file__).parent / (root.name + "-macro-transpositions.json")
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checked": checked, "affected": affected, "saved": str(target),
                      "first_example": {k: examples[0][k] for k in ("label", "discarded")} if examples else None}, indent=2))


if __name__ == "__main__":
    main()
