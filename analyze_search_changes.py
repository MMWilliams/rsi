"""Post-audit explanations of fixed-filter gains/losses; never selects a policy."""
import argparse
import json
from pathlib import Path

from rsi.common import ROOT, canonical, write_json
from rsi.retention_run import file_hash
from rsi.search import atom_pool
from rsi.atom_pool_partial import atom_pool as partial_pool
from dsl import render_atom
from parse import parse


def representable(program, pool):
    if not program:
        return False
    atoms = tuple(render_atom(a) for a in parse(program).atoms)
    pieces = {tuple(row["atoms"]) for row in pool}
    reached = {0}
    for index in range(len(atoms)):
        if index in reached:
            for end in range(index + 1, len(atoms) + 1):
                if atoms[index:end] in pieces:
                    reached.add(end)
    return len(atoms) in reached


def analyze(root):
    read = lambda name: json.loads((root / name).read_text())
    assert read("audit.json")["status"] == "passed"
    manifest = read("artifact_manifest.json")
    for name in ("graded.json", "protected_banks.json", "common_macros.json", "results.json"):
        assert file_hash(root / name) == manifest[name]["sha256"]
    for name in ("rsi/search.py", "rsi/atom_pool_partial.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"):
        assert file_hash(ROOT / name) == file_hash(root / "source" / name)
    macros = read("common_macros.json")
    rows = {}
    for row in read("graded.json"):
        rows.setdefault(row["task_id"], {})[row["arm"]] = row
    explanations, charge = [], 0
    for group, tasks in read("protected_banks.json").items():
        for task in tasks:
            arms = rows[task["id"]]
            old, new = arms["baseline@128"], arms["partial_empty@128"]
            if old["selected_correct"] == new["selected_correct"]:
                continue
            old_pool, c1 = atom_pool(canonical(task["visible"]), canonical(macros))
            new_pool, c2 = partial_pool(canonical(task["visible"]), canonical(macros))
            charge += c1 + c2
            old_program = old["frontier"][0]["program"] if old["frontier"] else ""
            new_program = new["frontier"][0]["program"] if new["frontier"] else ""
            in_old = representable(new_program, old_pool)
            loss = old["selected_correct"]
            old_in_new_frontier = any(f["program"] == old_program for f in new["frontier"])
            old_at_512 = any(f["program"] == old_program for f in arms["partial_empty@512"]["frontier"])
            if not loss:
                mechanism = "new_selected_program_outside_old_filtered_pool" if not in_old else "search_order_or_discovery_changed_with_expanded_pool"
            elif old_in_new_frontier:
                mechanism = "correct_old_program_found_but_ranked_below_new_first_choice"
            elif old_at_512:
                mechanism = "correct_old_program_absent_at_128_but_present_at_512"
            else:
                mechanism = "correct_old_program_absent_from_recorded_corrected_frontiers"
            explanations.append({"task_id": task["id"], "seed_group": group, "change": "loss" if loss else "win",
                "visible": task["visible"], "old_program": old_program, "new_program": new_program,
                "new_program_representable_in_old_pool": in_old,
                "old_program_representable_in_new_pool": representable(old_program, new_pool),
                "old_program_in_new_frontier128": old_in_new_frontier, "old_program_in_new_frontier512": old_at_512,
                "corrected_coverage64_at128": any(f["oracle_correct"] for f in new["frontier"]),
                "corrected_coverage64_at512": any(f["oracle_correct"] for f in arms["partial_empty@512"]["frontier"]),
                "mixture_selected_correct": arms["mixture@128"]["selected_correct"],
                "mixture_coverage64": any(f["oracle_correct"] for f in arms["mixture@128"]["frontier"]),
                "mechanism_evidence": mechanism, "old_cost": old["cost"], "new_cost": new["cost"]})
    return {"source_run": str(root), "analysis_code_sha256": file_hash(Path(__file__)),
            "source_sha256": {name: file_hash(root / name) for name in ("results.json", "audit.json", "graded.json", "protected_banks.json")},
            "pool_primitive_charges": charge, "changed_first_choices": len(explanations),
            "mechanism_counts": {key: sum(r["mechanism_evidence"] == key for r in explanations) for key in sorted({r["mechanism_evidence"] for r in explanations})},
            "records": explanations,
            "limits": "Post-outcome descriptive analysis of exact program syntax and saved capped frontiers. Does not prove why a program generalizes, all-input correctness or completeness of search. No new hidden grading or policy selection."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("output")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    result = analyze(Path(args.run))
    write_json(output, result)
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))
