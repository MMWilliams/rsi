import collections
import copy
import json
import shutil

import pytest

from audit_library import audit
from rsi.common import ROOT, canonical, digest, write_json
from rsi.library import harvest_memory, rank_memory, scramble_memory
from rsi.library_run import run
from rsi.retention_run import seal_artifacts
from dsl import render_atom
from parse import parse


def test_fragment_memory_requires_verified_whole_solution_and_keeps_provenance():
    evaluation = {"label": "fixture/harvest", "request_sha256": "request",
                  "results": [{"task_id": "yes", "oracle_correct": True, "program": "Concat(Sub(C0,C1), '-', Sub(C1,C2))"},
                              {"task_id": "no", "oracle_correct": False, "program": "Concat('bad', 'solution')"}]}
    memory, additions = harvest_memory({}, evaluation)
    assert len(memory) == 3 and len(additions) == 3
    assert all(entry["task_id"] == "yes" and entry["program_sha256"] == digest(evaluation["results"][0]["program"])
               for records in memory.values() for entry in records)
    same, duplicate_additions = harvest_memory(memory, evaluation)
    assert same == memory and not duplicate_additions


def test_scrambled_control_preserves_atom_multiset_and_labels_corruption():
    memory = {"Concat(Sub(C0,C1), '-')": [{"task_id": "a", "request_sha256": "r"}],
              "Concat(Sub(C1,C2), '/')": [{"task_id": "b", "request_sha256": "s"}]}
    output, trace = scramble_memory(memory, 27)
    original = collections.Counter(render_atom(a) for t in memory for a in parse(t).atoms)
    scrambled = collections.Counter(render_atom(a) for r in trace["entries"] for a in parse(r["scrambled"]).atoms)
    assert scrambled == original
    assert all("scrambled_from" in c for records in output.values() for c in records)
    assert (output, trace) == scramble_memory(memory, 27)


def test_ranking_rejects_hidden_data_even_with_empty_memory():
    with pytest.raises(ValueError, match="public"):
        rank_memory({}, [{"id": "x", "visible": [], "hidden": []}], [])


@pytest.fixture(scope="module")
def library_archive(tmp_path_factory):
    root = tmp_path_factory.mktemp("library-audit")
    config = json.loads((ROOT / "configs/library-v7.json").read_text())
    config.update(seeds=[181], search_budget=8, bank_seed=817291,
                  bank_counts={**{f"{phase}_{split}": 6 for phase in ("source", "transfer") for split in ("harvest", "development", "admission")}, "final": 2})
    run(config, root)
    return root


def test_real_library_run_regrades_and_reconstructs_all_changes(library_archive):
    result = audit(library_archive)
    assert result["status"] == "passed"
    assert result["trajectories"] == 7 and result["edit_attempts"] == 84
    assert result["evaluation_batches"] == 267 and result["search_outputs_regraded"] == 282


@pytest.mark.parametrize("forgery", ["inherited_memory", "ranking", "early_final"])
def test_library_audit_rejects_semantic_forgery_after_resealing(library_archive, tmp_path, forgery):
    root = tmp_path / "forged"
    shutil.copytree(library_archive, root)
    if forgery == "inherited_memory":
        rows = json.loads((root / "trajectories.json").read_text())
        entry = next(r for r in rows if r["condition"] == "g6")
        entry["trajectory"]["snapshots"]["0"]["memory"]["Concat('forged', '-')"] = []
        write_json(root / "trajectories.json", rows)
    else:
        events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
        if forgery == "ranking":
            event = next(e for e in events if e["kind"] == "fragment_proposals")
            event["payload"]["ranking_primitive_upper_bound"] += 1
        else:
            closed = next(i for i, e in enumerate(events) if e["kind"] == "optimization_closed")
            final = next(i for i, e in enumerate(events) if e["kind"] == "evaluation" and e["payload"]["label"].startswith("final/"))
            events.insert(closed, events.pop(final))
        previous = "0" * 64
        for i, event in enumerate(events):
            event.pop("sha256")
            event.update(seq=i, previous=previous)
            event["sha256"] = digest(event)
            previous = event["sha256"]
        (root / "events.jsonl").write_text("\n".join(canonical(e) for e in events) + "\n", encoding="utf-8")
    seal_artifacts(root)
    with pytest.raises(AssertionError):
        audit(root)
