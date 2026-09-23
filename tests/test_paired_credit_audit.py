"""Rehash a copied probe and require the independent audit to catch semantic edits."""
import copy
import json
import shutil

import pytest

from audit_paired_credit import audit
from rsi.common import ROOT, canonical, digest, write_json
from rsi.retention_run import seal_artifacts


FIXTURE = ROOT / "analysis/paired-credit-fixture-20260916"


def reseal(root, events, result):
    events[-1]["payload"] = {"results_sha256": digest(result)}
    previous = "0" * 64
    for index, event in enumerate(events):
        event.pop("sha256", None)
        event["seq"], event["previous"] = index, previous
        event["sha256"] = digest(event)
        previous = event["sha256"]
    (root / "events.jsonl").write_text("\n".join(canonical(e) for e in events) + "\n", encoding="utf-8")
    write_json(root / "results.json", result)
    seal_artifacts(root)


def test_original_fixture_passes_independent_audit(tmp_path):
    root = tmp_path / "original"
    shutil.copytree(FIXTURE, root)
    assert audit(root)["paired_effects_recomputed"] == 12


def test_resealed_fabricated_later_improvement_is_rejected(tmp_path):
    root = tmp_path / "fabricated_effect"
    shutil.copytree(FIXTURE, root)
    result = json.loads((root / "results.json").read_text())
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    result["pairs"][0]["later_improvement"] += 1
    reseal(root, events, result)
    with pytest.raises(AssertionError):
        audit(root)


def test_resealed_early_measurement_is_rejected(tmp_path):
    root = tmp_path / "early_measurement"
    shutil.copytree(FIXTURE, root)
    result = json.loads((root / "results.json").read_text())
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    closed = next(i for i, event in enumerate(events) if event["kind"] == "optimization_closed")
    measurement = next(i for i, event in enumerate(events) if event["kind"] == "evaluation" and event["payload"]["split"].endswith("measurement"))
    event = events.pop(measurement)
    events.insert(closed, event)
    reseal(root, events, result)
    with pytest.raises(AssertionError, match="Measurement leaked"):
        audit(root)
