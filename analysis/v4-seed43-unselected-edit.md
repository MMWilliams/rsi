# transfer/g6/10043/g3/p0

Run: `inheritance-20260916-v4`
Explanation script SHA-256: `a1d210cbb1cf305cc223e77af0f9efdae1e2fc0d90b7a44a6479bd0eddc51ad8`
Journal head at rendering: `049f43b1a0db8541dbc9bb481acd6596ea0c085b2a0da7d7ec3a516959f85e94`
Journal events: 1474 (proposed), 1480 (resolved).
Resolution hash: `718d21e895371f688ec6e4be23ceeb6acd8d03baf6e3fb2747cff467e6c9fb8b`

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

This archive predates selection traces. The outcome is recorded, but the draw/ranking explanation is unavailable.

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

Parent 9/16; candidate 9/16. Wins: 0; losses: 0.
Evaluation events: 1473 and 1475; matched by both request hash and trajectory label.
Gained task IDs: none.
Lost task IDs: none.

Candidate evaluation cost record (logical counts; worker time excludes host grading):
```json
{
  "incidents": 0,
  "model_proposal_checks": 0,
  "oracle_string_executions": 256,
  "primitive_executions": 147916,
  "replay_batches": 1,
  "search_expansions": 2056,
  "wall_seconds": 0.2676819000043906,
  "worker_batches": 2
}
```

Admission: candidate not evaluated.

## Statistics

```json
{
  "before": {
    "accepted": 0,
    "beneficial": 0,
    "descendant_gain_sum": 0.0,
    "descendant_trials": 0,
    "gain_sum": -0.1875,
    "trials": 6
  },
  "after": {
    "accepted": 0,
    "beneficial": 0,
    "descendant_gain_sum": 0.0,
    "descendant_trials": 0,
    "gain_sum": -0.1875,
    "trials": 7
  }
}
```

The complete-run audit separately checks these statistics and selection traces. A valid journal chain alone does not establish correctness.
