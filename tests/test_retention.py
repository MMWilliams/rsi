import pytest

from rsi.retention import coverage_decision, measure, verified_pool, resolve_update
from rsi.neural import adapter_hash


def score(counts):
    from rsi.neural import pass_at_k
    rows = [{"id": str(i), "n": 64, "correct": c,
             "pass_at_k": {str(k): pass_at_k(64, c, k) for k in (1, 64)}} for i, c in enumerate(counts)]
    return {"tasks": rows, "pass_at_k": {str(k): sum(r["pass_at_k"][str(k)] for r in rows) / len(rows) for k in (1, 64)}}


def test_gate_rejects_lost_task_even_when_total_coverage_and_pass1_improve():
    decision = coverage_decision(score([1, 0, 0]), score([0, 20, 20]))
    assert not decision["eligible"]
    assert decision["lost_task_ids"] == ["0"]
    assert decision["pass_k_delta"] > 0


def test_gate_rejects_tie_and_pass1_regression_but_accepts_retained_gain():
    assert not coverage_decision(score([1, 0]), score([1, 0]))["eligible"]
    assert not coverage_decision(score([30, 0]), score([1, 1]))["eligible"]
    assert coverage_decision(score([1, 0]), score([1, 1]))["eligible"]


def test_gate_rejects_mismatched_task_identity():
    candidate = score([2])
    candidate["tasks"][0]["id"] = "different"
    with pytest.raises(ValueError):
        coverage_decision(score([1]), candidate)


def test_replay_dedup_and_independent_reverification():
    task = {"id": "t", "visible": [["a", "a"]], "hidden": [["bc", "b"]]}
    row = {"task_id": "t", "program": "Concat(Sub(C0,C1))", "oracle_correct": True}
    assert len(verified_pool([[row], [row]], {"t": task})) == 1
    with pytest.raises(ValueError):
        verified_pool([[{**row, "program": "Concat('a')"}]], {"t": task})


def test_rejected_update_restores_exact_adapter_and_control_retains_candidate(tmp_path):
    import torch
    from peft import LoraConfig
    from transformers import Qwen3Config, Qwen3ForCausalLM
    from rsi.neural import LocalModel, make_adapters, ADAPTER_NAMES
    local = LocalModel.__new__(LocalModel)
    local.model = make_adapters(Qwen3ForCausalLM(Qwen3Config(vocab_size=32, hidden_size=32,
        intermediate_size=64, num_hidden_layers=1, num_attention_heads=4, num_key_value_heads=2, head_dim=8)),
        LoraConfig(r=2, lora_alpha=4, target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM"))
    parent = local.snapshot("search")
    local.activate("search")
    with torch.no_grad():
        for p in local.model.parameters():
            if p.requires_grad:
                p.add_(.125)
    candidate = local.snapshot("search")
    assert adapter_hash(candidate) != adapter_hash(parent)
    rejection = coverage_decision(score([1]), score([0]))
    result = resolve_update(local, "search", parent, rejection, True)
    assert result["rollback_verified"] and adapter_hash(local.snapshot("search")) == adapter_hash(parent)
    local.restore("search", candidate)
    result = resolve_update(local, "search", parent, rejection, False)
    assert result["accepted"] and adapter_hash(local.snapshot("search")) == adapter_hash(candidate)


def test_bank_exclusions_are_respected():
    from rsi.banks import create_banks, template
    config = {"bank_seed": 4, "bank_counts": {"final": 4}, "visible_examples": 3, "hidden_examples": 3, "max_atoms": 2}
    first, _ = create_banks(config)
    excluded = {template(r["reference"]) for r in first["final"]}
    second, _ = create_banks(config, excluded)
    assert not excluded & {template(r["reference"]) for r in second["final"]}
