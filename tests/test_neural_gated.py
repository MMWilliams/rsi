from run_neural_gated import merge_rows


def test_replay_pool_deduplicates_verified_targets():
    row = {"task_id": "a", "program": "Concat('.')", "oracle_correct": True}
    assert len(merge_rows([row], [row], [])) == 1
