# transfer/g0/10043/g3/p1

Run: `inheritance-20260916-v4`
Explanation script SHA-256: `a1d210cbb1cf305cc223e77af0f9efdae1e2fc0d90b7a44a6479bd0eddc51ad8`
Journal head at rendering: `049f43b1a0db8541dbc9bb481acd6596ea0c085b2a0da7d7ec3a516959f85e94`
Journal events: 1354 (proposed), 1359 (resolved).
Resolution hash: `963c4b433e8a4063465b40dc574a807640216f1feb2fbf19fc2512396cd83ef5`

This explains the implemented decision and recorded measurements. It does not prove the mechanism of an improvement.

## Proposed change

Hypothesis: This bounded edit improves solve rate at the fixed search budget
Operator: `match_cost_down`; origin: `initial`.

```json
{
  "match_cost": [
    "min",
    4.0,
    [
      "max",
      0.1,
      [
        "mul",
        "match_cost",
        0.65
      ]
    ]
  ]
}
```

## Why it was selected

This archive predates selection traces. The outcome is recorded, but the draw/ranking explanation is unavailable.

## Outcome

Accepted: **True**. Reason: `development_gain_and_admission_nonregression`.
Selected configuration hash: `07026a95bf29c738a5be14305c43ede07d0735142517882ed163d14fde7c2702`.

Configuration changes:
```json
{
  "match_cost": {
    "before": 1.0,
    "after": 0.65
  }
}
```

### Development

Parent 9/16; candidate 11/16. Wins: 2; losses: 0.
Evaluation events: 1351 and 1355; matched by both request hash and trajectory label.
Gained task IDs: a66cfd113da26f8831c6, 84597c4f8f5c587ab629.
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
  "wall_seconds": 0.22957949998090044,
  "worker_batches": 2
}
```

### Admission

Parent 10/16; candidate 10/16. Wins: 0; losses: 0.
Evaluation events: 1356 and 1357; matched by both request hash and trajectory label.
Gained task IDs: none.
Lost task IDs: none.

Candidate evaluation cost record (logical counts; worker time excludes host grading):
```json
{
  "incidents": 0,
  "model_proposal_checks": 0,
  "oracle_string_executions": 256,
  "primitive_executions": 148160,
  "replay_batches": 1,
  "search_expansions": 1544,
  "wall_seconds": 0.25821510000969283,
  "worker_batches": 2
}
```

## Statistics

```json
{
  "before": {
    "accepted": 0,
    "beneficial": 0,
    "descendant_gain_sum": 0.0,
    "descendant_trials": 0,
    "gain_sum": 0.0,
    "trials": 0
  },
  "after": {
    "accepted": 1,
    "beneficial": 1,
    "descendant_gain_sum": 0.0,
    "descendant_trials": 0,
    "gain_sum": 0.125,
    "trials": 1
  }
}
```

The complete-run audit separately checks these statistics and selection traces. A valid journal chain alone does not establish correctness.
