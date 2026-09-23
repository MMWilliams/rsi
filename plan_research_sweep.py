"""Create a reproducible exploratory plan across ML/RL/AI/CS frameworks.

This command plans experiments; it does not launch GPU jobs. Each planned
variant carries its full override record and can later be linked to a sealed
run and a findings-ledger entry.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, write_json
from rsi.research_frameworks import latin_hypercube

VARIABLE_SPACE = {
    "search_budget": {"values": [64, 128, 256, 512]},
    "max_atoms": {"values": [3, 4, 5]},
    "samples_per_task": {"values": [16, 32, 64, 128]},
    "max_new_tokens": {"values": [48, 96, 192]},
    "generation_batch_size": {"values": [8, 16, 32, 64]},
    "lora_steps": {"values": [16, 48, 96, 192]},
    "lora_batch_size": {"values": [4, 8, 16]},
    "anchor_per_batch": {"values": [1, 2, 4, 6]},
    "lora_learning_rate": {"low": 0.00003, "high": 0.0008},
    "search.progress_weight": {"low": 0.1, "high": 4.0},
    "search.widening": {"low": 0.25, "high": 1.0},
    "search.macro_discount": {"low": 0.0, "high": 0.8},
    "sampling.temperature": {"low": 0.2, "high": 1.2},
    "sampling.top_p": {"low": 0.6, "high": 1.0},
    "sampling.top_k": {"values": [0, 10, 20, 50]},
    "training.replay_mode": {"values": ["fresh", "cumulative", "prioritized", "novelty"]},
    "training.curriculum": {"values": ["uniform", "easy_to_hard", "hard_to_easy", "self_paced"]},
    "controller.algorithm": {"values": ["fixed", "ucb1", "thompson", "epsilon_greedy", "contextual_bandit"]},
    "controller.reward": {"values": ["pass_at_1", "pass_at_64", "pareto_coverage_cost", "novelty_adjusted"]},
    "program_search": {"values": ["best_first", "mcts", "beam", "enumerative", "novelty_search"]},
}

FRAMEWORKS = {
    "ml": ["factorial_ablation", "latin_hypercube", "multi_fidelity_successive_halving", "pareto_model_selection"],
    "rl": ["ucb1_bandit", "thompson_sampling", "contextual_bandit", "off_policy_replay", "self_paced_curriculum"],
    "ai": ["mcts_program_search", "novelty_search", "map_elites_archive", "self_consistency", "reflection_proposals"],
    "cs": ["program_synthesis", "mdl_complexity_penalty", "causal_ablation", "property_based_testing", "metamorphic_testing"],
}


def make_plan(base_config: dict, samples: int, seed: int) -> dict:
    rows = latin_hypercube(VARIABLE_SPACE, samples, seed)
    variants = [{
        "id": f"sweep-{index:04d}-{digest(row)[:12]}",
        "status": "planned",
        "overrides": row,
        "frameworks": list(FRAMEWORKS),
        "hypothesis": "Changing this factor may trade off verified coverage, retention, diversity, novelty and compute; the result is exploratory until replicated.",
        "primary_metrics": ["pass_at_1", "pass_at_64", "coverage", "distinct_programs", "generated_tokens", "training_steps", "wall_seconds"],
    } for index, row in enumerate(rows, 1)]
    variants.insert(0, {
        "id": "baseline-frontier-v11",
        "status": "reference",
        "overrides": {},
        "frameworks": ["existing_audited_pipeline"],
        "hypothesis": "Reference condition for all exploratory contrasts.",
        "primary_metrics": ["pass_at_1", "pass_at_64", "coverage", "distinct_programs", "generated_tokens", "training_steps", "wall_seconds"],
    })
    return {
        "schema_version": 1,
        "status": "planned_not_executed",
        "base_config": base_config,
        "seed": seed,
        "requested_variants": samples,
        "variable_space": VARIABLE_SPACE,
        "framework_catalog": FRAMEWORKS,
        "variants": variants,
        "guardrails": [
            "Exploratory variants cannot overwrite sealed historical runs.",
            "Every completed variant requires an independent audit before entering the observed findings ledger.",
            "Primary comparisons use a matched vector budget; scalar cost is descriptive only.",
            "No final-task result may select a checkpoint or tune a variant.",
            "Negative and null results are retained.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/frontier-v11.json")
    parser.add_argument("--output", default="analysis/research-sweep-v13-plan.json")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260917)
    args = parser.parse_args()
    base = json.loads(Path(args.config).read_text(encoding="utf-8"))
    write_json(Path(args.output), make_plan(base, args.samples, args.seed))
