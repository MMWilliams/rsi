# transfer/g6/10101/g1/p0

Run: `inheritance-20260916-v5`
Explanation script SHA-256: `a1d210cbb1cf305cc223e77af0f9efdae1e2fc0d90b7a44a6479bd0eddc51ad8`
Journal head at rendering: `bbc6485449f02b5943b57e8f061eac50cd73b0c60a403ca33628ba86146d5a79`
Journal events: 364 (proposed), 370 (resolved).
Resolution hash: `026b8a79d9ef1a1350fb849e010a32303f4e3fa6622d590d57b382bd66fd4f04`

This explains the implemented decision and recorded measurements. It does not prove the mechanism of an improvement.

## Proposed change

Hypothesis: This bounded edit improves solve rate at the fixed search budget
Operator: `absolute_cost_down`; origin: `initial`.

```json
{
  "absolute_cost": [
    "min",
    4.0,
    [
      "max",
      0.1,
      [
        "mul",
        "absolute_cost",
        0.65
      ]
    ]
  ]
}
```

## Why it was selected

maximum_sampled_productivity_plus_mean_gain_plus_quarter_descendant_mean; lexical_name_tiebreak

Effect-table hash: `7730f4f54751e1b5041f2653f67862e73601799b27d198c10f8c7dc9415a5074`
RNG before/after: `f6c132feccc700b3691171a001ba350457cc15e479da7e4a5bd65a34905994af` / `1edec00420e8efba0963d33e00eadb16dfc969e0fb48d1840b4da9462e11cde7`

| Operator | Beta draw | Mean gain | Descendant mean | Combined score | Chosen |
|---|---:|---:|---:|---:|---|
| absolute_cost_down | 0.675469 | 0.031250 | 0.000000 | 0.706719 | yes |
| absolute_cost_up | 0.181588 | -0.010417 | 0.000000 | 0.171171 |  |
| match_cost_down | 0.096196 | -0.020833 | 0.062500 | 0.090988 |  |
| match_cost_up | 0.001371 | 0.000000 | 0.000000 | 0.001371 |  |
| constant_cost_down | 0.041973 | 0.000000 | 0.000000 | 0.041973 |  |
| constant_cost_up | 0.161345 | -0.010417 | 0.000000 | 0.150928 |  |
| case_cost_down | 0.255243 | 0.000000 | 0.000000 | 0.255243 |  |
| case_cost_up | 0.139951 | 0.000000 | 0.000000 | 0.139951 |  |
| progress_weight_down | 0.235380 | -0.010417 | 0.000000 | 0.224964 |  |
| progress_weight_up | 0.041830 | 0.000000 | 0.000000 | 0.041830 |  |
| widening_down | 0.284431 | 0.000000 | 0.000000 | 0.284431 |  |
| widening_up | 0.084879 | 0.010417 | 0.062500 | 0.110920 |  |

Scores are selection heuristics, not calibrated probabilities of future improvement.

## Outcome

Accepted: **False**. Reason: `not_selected_after_development_comparison`.
Selected configuration hash: `1744faad7aacb5ca34e8782ee9ec857eed5c92e499b051aafac4d05a61135461`.

Configuration changes:
```json
{
  "absolute_cost": {
    "before": 1.0,
    "after": 0.65
  }
}
```

### Development

Parent 12/16; candidate 12/16. Wins: 0; losses: 0.
Evaluation events: 363 and 365; matched by both request hash and trajectory label.
Gained task IDs: none.
Lost task IDs: none.

Candidate evaluation cost record (logical counts; worker time excludes host grading):
```json
{
  "incidents": 0,
  "model_proposal_checks": 0,
  "oracle_string_executions": 256,
  "primitive_executions": 147012,
  "replay_batches": 1,
  "search_expansions": 1920,
  "wall_seconds": 0.32368960001622327,
  "worker_batches": 2
}
```

Admission: candidate not evaluated.

## Statistics

```json
{
  "before": {
    "accepted": 1,
    "beneficial": 3,
    "descendant_gain_sum": 0.0,
    "descendant_trials": 0,
    "gain_sum": 0.1875,
    "trials": 6
  },
  "after": {
    "accepted": 1,
    "beneficial": 3,
    "descendant_gain_sum": 0.0,
    "descendant_trials": 0,
    "gain_sum": 0.1875,
    "trials": 7
  }
}
```

The complete-run audit separately checks these statistics and selection traces. A valid journal chain alone does not establish correctness.
