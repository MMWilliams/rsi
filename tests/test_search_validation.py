import json
import pytest

from rsi.common import ROOT, Journal, write_json
from rsi.retention_run import seal_artifacts
from run_search_validation import combine, run
from audit_search_validation import audit


def test_mixture_deduplicates_and_cannot_consult_grades():
    a = {"program": "Concat('-')", "cost": 2.0, "visible_outputs": ["-"], "source": "search"}
    b = {**a, "cost": 1.0}
    assert combine([a], [b]) == [b]
    with pytest.raises(ValueError, match="ungraded"):
        combine([{**a, "oracle_correct": True}], [])


def test_fresh_audit_and_resealed_omission(tmp_path):
    config = json.loads((ROOT / "configs/search-validation-v8.json").read_text())
    config.update(seeds=[771], tasks_per_seed=2)
    root = tmp_path / "verification_fixture_not_replication"
    run(config, root)
    report = audit(root)
    assert report["status"] == "passed" and report["searches_reexecuted"] == 16
    records = json.loads((root / "searches.json").read_text())
    records.pop()
    write_json(root / "searches.json", records)
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    target = max(i for i, row in enumerate(events) if row["kind"] == "search")
    events.pop(target)
    (root / "events.jsonl").unlink()
    journal = Journal(root / "events.jsonl")
    for row in events:
        journal.append(row["kind"], row["payload"])
    seal_artifacts(root)
    with pytest.raises(AssertionError):
        audit(root)
