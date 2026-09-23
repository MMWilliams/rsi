"""Replay unified policy decisions against two separately audited transfer archives."""
from __future__ import annotations

import json
from rsi.common import ROOT
from unified_top5_policy import predict, select_semantic, select_encoded


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    semantic = "runs/policy-transfer-20260917b"
    encoded = "runs/encoding-combination-20260917"
    assert read(semantic + "/audit.json")["status"] == "passed"
    assert read(encoded + "/audit.json")["status"] == "passed"
    sr = read(semantic + "/results.json")
    sp = read(semantic + "/candidate_pools.json")
    weights = sr["policies"]["top4_semantic"]["selected_weights"]
    semantic_checked = 0
    for split, policies in sr["transfer"].items():
        for expected in policies["top4_semantic"]["selected"]["rows"]:
            candidate = select_semantic(sp[expected["task_id"]], weights)
            assert (candidate["program"] if candidate else "") == expected["program"]
            assert (candidate["source"] if candidate else "none") == expected["source"]
            semantic_checked += 1
    er = read(encoded + "/results.json")
    ep = read(encoded + "/candidate_pools.json")
    encoded_checked = 0
    for expected in er["summary"]["combined"]["rows"]:
        source, candidate = select_encoded(ep[expected["task_id"]])
        assert source == expected["source"] and (candidate["program"] if candidate else "") == expected["program"]
        encoded_checked += 1
    semantic_task = read(semantic + "/protected_banks.json")["transfer_203212"][0]
    semantic_expected = sr["transfer"]["transfer_203212"]["top4_semantic"]["selected"]["rows"][0]
    semantic_live = predict(semantic_task, "semantic", semantic_weights=weights, lineage_library=[])
    assert semantic_live == {key: semantic_expected[key] for key in ("program", "source")}
    encoded_task = read(encoded + "/protected_banks.json")["final"][0]
    encoded_expected = er["summary"]["combined"]["rows"][0]
    library = read("runs/generic-body-evolution-v86-encoding-adaptive-20261017/generic_lineage_library.json")
    encoded_live = predict(encoded_task, "encoded", semantic_weights=weights, lineage_library=library)
    assert encoded_live == {key: encoded_expected[key] for key in ("program", "source")}
    return {"status": "passed", "semantic_decisions": semantic_checked, "encoded_decisions": encoded_checked,
            "live_task_replays": 2, "scope": "decision replay over independently audited pools plus one live task per lane"}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
