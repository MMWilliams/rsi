"""Check candidate completeness, source-only grades and verified cache reuse."""
import argparse
import json
from pathlib import Path

from audit_library import rebuild_rankings
from audit_results import published_correct
from rsi.common import digest, verify_journal, write_json
from rsi.retention_run import file_hash


def audit(root):
    root = Path(root)
    read = lambda base, name: json.loads((Path(base) / name).read_text(encoding="utf-8"))
    manifest = read(root, "artifact_manifest.json")
    for name, record in manifest.items():
        assert file_hash(root / name) == record["sha256"] and (root / name).stat().st_size == record["bytes"], "Artifact changed"
    count = verify_journal(root / "events.jsonl")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[0]["kind"] == "started" and events[-1]["kind"] == "completed"
    started = events[0]["payload"]
    source, reuse = Path(started["source"]), Path(started["reuse"])
    for base, field in ((source, "source_artifacts"), (reuse, "reuse_artifacts")):
        assert read(base, "audit.json")["status"] == "passed"
        prior_manifest = read(base, "artifact_manifest.json")
        for name, value in started[field].items():
            assert file_hash(base / name) == value
            if name in prior_manifest:
                assert value == prior_manifest[name]["sha256"]
    for name, value in started["code_sha256"].items():
        assert file_hash(root / "source" / name) == value
    for name in ("rsi/search.py", "rsi/search_reopen.py", "rsi/common.py", "rsi/oracle.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"):
        assert file_hash(root / "source" / name) == file_hash(reuse / "source" / name), "Invalid cache dependency"
    tasks = read(source, "protected_banks.json")["source_development"]
    assert read(root, "source_tasks.json") == tasks == read(reuse, "source_tasks.json")
    by_id = {t["id"]: t for t in tasks}
    parents = {}
    for line in (source / "events.jsonl").open(encoding="utf-8"):
        event = json.loads(line)
        payload = event["payload"]
        if event["kind"] == "evaluation" and payload["label"].startswith("source/") and payload["label"].endswith("/parent"):
            parents[payload["label"][:-7]] = payload["request"]
    expected_plan = []
    for entry in read(source, "trajectories.json"):
        if entry["phase"] != "source":
            continue
        trajectory = entry["trajectory"]
        for decision in trajectory["decisions"]:
            label = decision["label"]
            request = parents[label]
            assert request["budget"] == 128 and request["max_atoms"] == 4 and request["proposals"] == {}
            memory = trajectory["snapshots"][str(decision["generation"])]["memory"]
            ranking, charge = rebuild_rankings(memory, request["tasks"], request["macros"])
            selected = {a["proposal"]["name"] for a in decision["attempts"] if a["proposal"]["kind"] == "add_fragment"}
            candidates = [{**r, "originally_selected": r["fragment"] in selected} for r in ranking if r["compatible_tasks"]]
            expected_plan.append({"label": label, "source_seed": entry["seed"], "request": request,
                                  "memory_sha256": digest(memory), "rankings": ranking, "candidates": candidates,
                                  "ranking_primitive_upper_bound": charge})
    plan = read(root, "plan.json")
    assert plan == expected_plan and digest(plan) == started["plan_sha256"], "Candidate completeness/ranking mismatch"
    assert len(plan) == 36 and sum(len(e["candidates"]) for e in plan) == 60
    prior = {}
    for line in (reuse / "events.jsonl").open(encoding="utf-8"):
        event = json.loads(line)
        if event["kind"] == "evaluation":
            prior[event["payload"]["request_sha256"]] = event["payload"]
    evaluated, fresh, reused = {}, 0, 0
    expected_order = []
    for entry in plan:
        requests = [entry["request"], *[{**entry["request"], "macros": sorted([*entry["request"]["macros"], c["fragment"]])} for c in entry["candidates"]]]
        for request in requests:
            expected_order.append(("evaluation_reused" if digest(request) in prior else "evaluation_fresh", request))
        expected_order.append(("menu_closed", {"label": entry["label"], "candidates": len(entry["candidates"])}))
    assert len(events[1:-1]) == len(expected_order)
    for event, (kind, expected) in zip(events[1:-1], expected_order):
        assert event["kind"] == kind
        payload = event["payload"]
        if kind == "menu_closed":
            assert payload == expected
            continue
        request = payload["request"]
        key = digest(request)
        assert request == expected and key == payload["request_sha256"] and key not in evaluated
        if kind == "evaluation_reused":
            assert payload == prior[key], "Reused payload changed"
            reused += len(payload["results"])
        else:
            assert key not in prior
            fresh += len(payload["results"])
        assert payload["replay_verified"] is True and len(payload["results"]) == len(request["tasks"])
        total = 0
        for task, row in zip(request["tasks"], payload["results"]):
            protected = by_id[task["id"]]
            assert task == {"id": protected["id"], "visible": protected["visible"]}
            assert row["task_id"] == task["id"] and row["kernel"] == "cost_reopening_v1"
            assert digest({k: v for k, v in row.items() if k not in ("oracle_correct", "replay_sha256")}) == row["replay_sha256"]
            grade = published_correct(row["program"], protected["visible"] + protected["hidden"])
            assert row["oracle_correct"] is grade
            assert 0 <= row["cost"]["expansions"] <= 128
            total += int(grade)
        assert payload["correct"] == total
        evaluated[key] = payload
    result = read(root, "results.json")
    expected_menus = []
    for entry in plan:
        request = entry["request"]
        parent = evaluated[digest(request)]
        candidates = []
        for candidate in entry["candidates"]:
            key = digest({**request, "macros": sorted([*request["macros"], candidate["fragment"]])})
            child = evaluated[key]
            pairs = list(zip(parent["results"], child["results"]))
            wins = [a["task_id"] for a, b in pairs if b["oracle_correct"] and not a["oracle_correct"]]
            losses = [a["task_id"] for a, b in pairs if a["oracle_correct"] and not b["oracle_correct"]]
            candidates.append({"fragment": candidate["fragment"], "originally_selected": candidate["originally_selected"],
                               "request_sha256": key, "correct": child["correct"], "wins": wins, "losses": losses,
                               "gain": (child["correct"] - parent["correct"]) / len(request["tasks"]),
                               "changed_programs": sum(a["program"] != b["program"] for a, b in pairs)})
        expected_menus.append({"label": entry["label"], "source_seed": entry["source_seed"], "parent_request_sha256": digest(request),
                               "parent_correct": parent["correct"], "n": len(request["tasks"]), "candidates": candidates,
                               "all_available_upper_bound": max([0.0] + [c["gain"] for c in candidates]),
                               "original_top_two_upper_bound": max([0.0] + [c["gain"] for c in candidates if c["originally_selected"]])})
    assert result["menus"] == expected_menus, "Paired candidate result mismatch"
    flat = [c for m in expected_menus for c in m["candidates"]]
    expected_totals = {"menu_count": 36, "candidate_count": 60, "unselected_count": sum(not c["originally_selected"] for c in flat),
                       "positive_candidates": sum(c["gain"] > 0 for c in flat), "negative_candidates": sum(c["gain"] < 0 for c in flat),
                       "positive_unselected": sum(c["gain"] > 0 and not c["originally_selected"] for c in flat),
                       "menus_with_opportunity": sum(m["all_available_upper_bound"] > 0 for m in expected_menus),
                       "mean_all_available_upper_bound": sum(m["all_available_upper_bound"] for m in expected_menus) / 36,
                       "mean_original_top_two_upper_bound": sum(m["original_top_two_upper_bound"] for m in expected_menus) / 36,
                       "changed_candidate_programs": sum(c["changed_programs"] for c in flat),
                       "fresh_outputs": fresh, "reused_outputs": reused, "fresh_replay_outputs": fresh,
                       "logical_charges_including_replay": {name: 2 * sum(r["cost"][name] for e in evaluated.values() for r in e["results"]) for name in ("expansions", "primitive_executions", "generated_nodes")}}
    for key, value in expected_totals.items():
        assert result[key] == value, "Metric/accounting mismatch: " + key
    assert fresh == 416 and reused == 1120
    assert events[-1]["payload"] == {"results_sha256": digest(result)}
    report = {"status": "passed", "artifacts_hashed": len(manifest), "journal_events": count,
              "source_menus": 36, "complete_candidate_set": 60, "task_outputs_regraded": fresh + reused,
              "fresh_outputs": fresh, "reused_outputs": reused,
              "limits": "Reconstructs all eligible single additions and regrades saved outputs; does not independently rerun searches, authenticate the host or cover combined additions."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Assertions must remain enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(parser.parse_args().run), indent=2))
