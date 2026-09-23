from rsi.evolving_domain import create_evolving_banks


def test_disjoint_transition_domain_uses_new_alphabet():
    config = {"bank_seed": 77, "bank_counts": {"train": 1, "final": 3},
              "visible_examples": 3, "hidden_examples": 2,
              "train_family": "delimiter", "eval_family": "transition_disjoint"}
    banks, _ = create_evolving_banks(config)
    texts = [text for text, _target in banks["final"][0]["visible"]]
    assert any(any("α" <= char <= "μ" for char in text) for text in texts)
    assert any(any(char in "٠١٢٣٤٥٦٧٨٩" for char in text) for text in texts)
    assert all(task["reference"].startswith("transition:") for task in banks["final"])
