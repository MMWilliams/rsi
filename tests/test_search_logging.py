from rsi.common import Journal, verify_journal
from rsi.evolution import evolve
from rsi.search import BASE_CONFIG


class Evaluator:
    def __init__(self, journal):
        self.journal = journal

    def evaluate(self, tasks, config, label, **kwargs):
        from rsi.common import digest
        score = int(config["progress_weight"] > BASE_CONFIG["progress_weight"])
        return {"request_sha256": digest([tasks, config, label]), "correct": score, "n": 1, "accuracy": float(score)}


def test_every_search_attempt_has_lineage_outcome_and_reason_including_repeated_operator(tmp_path):
    import json
    journal = Journal(tmp_path / "events.jsonl")
    operator = {"name": "improve", "origin": "initial", "updates": {"progress_weight": ["mul", "progress_weight", 1.1]}}
    result = evolve(Evaluator(journal), {"development": [{"id": "d"}], "admission": [{"id": "a"}]},
                    {"generations": 1, "proposals_per_generation": 2}, 17, catalog=[operator])
    events = [json.loads(line) for line in journal.path.read_text().splitlines()]
    proposals = [e["payload"] for e in events if e["kind"] == "search_change_proposed"]
    resolutions = [e["payload"] for e in events if e["kind"] == "search_change_resolved"]
    assert len(proposals) == len(resolutions) == 2
    assert [r["change_id"] for r in proposals] == [r["change_id"] for r in resolutions]
    assert sum(r["accepted"] for r in resolutions) == 1
    assert all(r["parent_config"] == BASE_CONFIG and r["reason"] for r in resolutions)
    assert result["decisions"][0]["attempts"] == resolutions
    assert verify_journal(journal.path) == len(events)
