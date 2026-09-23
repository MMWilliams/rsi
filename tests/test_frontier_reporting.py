"""Reports must verify the evidence now, not trust a stale audit status."""
import json
import shutil

import pytest

from rsi.common import ROOT
from rsi.retention_run import file_hash, seal_artifacts
from summarize_frontier_distillation import summarize


FIXTURE = ROOT / "analysis/frontier-v9-verification-fixture-v2"


@pytest.mark.parametrize("reseal", [False, True])
def test_report_rejects_changed_pool_despite_previous_passing_audit(tmp_path, reseal):
    root = tmp_path / "stale_audit"
    shutil.copytree(FIXTURE, root)
    pool = root / "training_pools/baseline_selected_round1.json"
    rows = json.loads(pool.read_text())
    rows.append({**rows[-1], "task_id": "fabricated_task", "stratum": "harvest"})
    pool.write_text(json.dumps(rows), encoding="utf-8")
    if reseal:
        seal_artifacts(root)
    output = tmp_path / "invalid.md"
    with pytest.raises((AssertionError, ValueError)):
        summarize(root, output)
    assert not output.exists()
    assert not output.with_suffix(".json").exists()


def test_report_audits_current_evidence_without_requiring_old_audit_stamp(tmp_path):
    root = tmp_path / "valid_fixture"
    shutil.copytree(FIXTURE, root)
    (root / "audit.json").write_text(json.dumps({"status": "not_audited"}))
    output = tmp_path / "fixture_report.md"
    summarize(root, output)
    record = json.loads(output.with_suffix(".json").read_text())
    assert json.loads((root / "audit.json").read_text())["status"] == "passed"
    assert record["audit_receipt"]["artifact_manifest_sha256"] == file_hash(root / "artifact_manifest.json")
    assert record["audit_receipt"]["audit_sha256"] == file_hash(root / "audit.json")
    for name, sha in record["verified_evidence_sha256"].items():
        assert file_hash(root / name) == sha
    assert len(record["changes"]) == 8
    assert record["audit_receipt"]["audit_seconds"] > 0


def test_failed_run_cannot_publish_a_completed_report(tmp_path):
    root = tmp_path / "failed_fixture"
    shutil.copytree(FIXTURE, root)
    (root / "FAILED.json").write_text('{"type":"simulated"}')
    output = tmp_path / "report.md"
    with pytest.raises(ValueError, match="completed, nonfailed"):
        summarize(root, output)
    assert not output.exists()


def test_report_cannot_add_files_to_sealed_archive(tmp_path):
    root = tmp_path / "valid_fixture"
    shutil.copytree(FIXTURE, root)
    with pytest.raises(ValueError, match="outside"):
        summarize(root, root / "report.md")
    assert not (root / "report.md").exists()
