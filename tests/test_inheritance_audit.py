import json

import pytest

from audit_inheritance import audit
from rsi.common import ROOT, canonical, digest, write_json
from rsi.inheritance_run import run
from rsi.retention_run import seal_artifacts


@pytest.fixture(scope="module")
def small_archive(tmp_path_factory):
    root = tmp_path_factory.mktemp("inheritance-audit")
    config = json.loads((ROOT / "configs/inheritance-v4.json").read_text())
    config.update(seeds=[17], search_budget=8, bank_seed=827461, log_selection=True,
                  bank_counts={"source_development": 6, "source_admission": 6,
                               "transfer_development": 6, "transfer_admission": 6, "final": 2})
    run(config, root, publish_latest=False)
    return root


def test_full_archive_reconciles_real_search_outputs_and_every_edit(small_archive):
    result = audit(small_archive)
    assert result["status"] == "passed"
    assert result["edit_attempts_reconciled"] == 72 + 5 * 12
    assert result["evaluation_batches"] == 6 * 15 + 5 * 6 * 5 + 6
    assert result["selection_trace_reconciliation"] == "passed"


def test_effect_table_forgery_fails_even_after_resealing_archive(small_archive, tmp_path):
    import shutil
    root = tmp_path / "forged"
    shutil.copytree(small_archive, root)
    path = root / "source_trajectories.json"
    rows = json.loads(path.read_text())
    table = rows[0]["snapshots"]["3"]["table"]
    table[next(iter(table))]["gain_sum"] += 1
    write_json(path, rows)
    seal_artifacts(root)
    with pytest.raises(AssertionError):
        audit(root)


def test_final_evaluation_before_freeze_fails_even_with_valid_hash_chain(small_archive, tmp_path):
    import shutil
    root = tmp_path / "early-final"
    shutil.copytree(small_archive, root)
    path = root / "events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    closed = next(i for i, e in enumerate(events) if e["kind"] == "optimization_closed")
    final = next(i for i, e in enumerate(events) if e["kind"] == "evaluation" and e["payload"]["label"].startswith("final/"))
    events.insert(closed, events.pop(final))
    previous = "0" * 64
    for seq, event in enumerate(events):
        event.update(seq=seq, previous=previous)
        event.pop("sha256")
        event["sha256"] = digest(event)
        previous = event["sha256"]
    path.write_text("\n".join(canonical(e) for e in events) + "\n", encoding="utf-8")
    seal_artifacts(root)
    with pytest.raises(AssertionError):
        audit(root)
