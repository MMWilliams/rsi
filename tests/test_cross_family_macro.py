from run_cross_family_macro_v75 import create_cross_family_banks


def test_cross_family_bank_manifest_keeps_source_and_target_families_explicit():
    config = {"bank_seed": 3, "bank_counts": {"train": 1, "development": 1, "admission": 1, "final": 1},
              "visible_examples": 4, "hidden_examples": 2,
              "families": {"train": "macro_transition", "development": "macro_transition",
                           "admission": "novel_operator_transition", "final": "novel_operator_transition"}}
    banks, metadata = create_cross_family_banks(config)
    assert metadata["development"]["family"] == "macro_transition"
    assert metadata["final"]["family"] == "novel_operator_transition"
    assert banks["development"][0]["reference"].startswith("macro:")
    assert banks["final"][0]["reference"].startswith("novel_operator:")
