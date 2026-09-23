import json
import shutil

import pytest

from audit_fragment_headroom import audit
from rsi.common import ROOT, canonical, digest, write_json
from rsi.retention_run import seal_artifacts


def test_complete_headroom_archive_reconciles_missing_counterfactuals():
    result = audit(ROOT / "runs/fragment-headroom-20260916-v7")
    assert result["complete_candidate_set"] == 60
    assert result["fresh_outputs"] == 416 and result["reused_outputs"] == 1120


@pytest.mark.parametrize("forgery", ["candidate_omission", "reused_payload"])
def test_omissions_and_changed_reused_outputs_rejected_after_resealing(tmp_path, forgery):
    root = tmp_path / "forged"
    shutil.copytree(ROOT / "runs/fragment-headroom-20260916-v7", root)
    if forgery == "candidate_omission":
        plan = json.loads((root / "plan.json").read_text())
        next(p for p in plan if p["candidates"])["candidates"].pop()
        write_json(root / "plan.json", plan)
        message = "Candidate completeness"
    else:
        events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
        changed = next(e for e in events if e["kind"] == "evaluation_reused")
        changed["payload"]["results"][0]["cost"]["expansions"] += 1
        previous = "0" * 64
        for i, event in enumerate(events):
            event.pop("sha256")
            event.update(seq=i, previous=previous)
            event["sha256"] = digest(event)
            previous = event["sha256"]
        (root / "events.jsonl").write_text("\n".join(canonical(e) for e in events) + "\n", encoding="utf-8")
        message = "Reused payload"
    seal_artifacts(root)
    with pytest.raises(AssertionError, match=message):
        audit(root)
