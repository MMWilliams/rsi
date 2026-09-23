import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("peft")
pytest.importorskip("transformers")

from peft import LoraConfig, get_peft_model_state_dict
from transformers import Qwen3Config, Qwen3ForCausalLM

from rsi.neural import ADAPTER_NAMES, identify_operator, make_adapters


def test_adapter_arms_have_identical_precision_and_no_state_key_collisions():
    config = Qwen3Config(vocab_size=32, hidden_size=32, intermediate_size=64, num_hidden_layers=1,
                        num_attention_heads=4, num_key_value_heads=2, head_dim=8)
    model = make_adapters(Qwen3ForCausalLM(config).to(torch.bfloat16),
                          LoraConfig(r=2, lora_alpha=4, target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM"))
    states = {logical: get_peft_model_state_dict(model, adapter_name=actual) for logical, actual in ADAPTER_NAMES.items()}
    expected = states["bootstrap"]
    assert len(expected) == 4
    for state in states.values():
        assert set(state) == set(expected)
        assert all(value.dtype == torch.float32 and torch.equal(value, expected[key]) for key, value in state.items())
    model.set_adapter(ADAPTER_NAMES["search"])
    trainable = [(name, value) for name, value in model.named_parameters() if value.requires_grad]
    assert trainable and all(".amplified." in name and ".lora_" in name for name, _ in trainable)
    frozen_before = {key: value.clone() for key, value in states["fixed_search"].items()}
    with torch.no_grad():
        for _, value in trainable:
            value.add_(0.125)
    frozen_after = get_peft_model_state_dict(model, adapter_name=ADAPTER_NAMES["fixed_search"])
    assert all(torch.equal(value, frozen_before[key]) for key, value in frozen_after.items())


def test_model_operator_identity_depends_on_expression_not_supplied_name():
    first = {"name": "same", "origin": "model", "updates": {"match_cost": ["mul", "match_cost", 0.8]}}
    second = {**first, "updates": {"match_cost": ["mul", "match_cost", 0.9]}}
    assert identify_operator(first)["name"] != identify_operator(second)["name"]
    assert identify_operator(first)["name"] == identify_operator({**first, "name": "renamed"})["name"]
