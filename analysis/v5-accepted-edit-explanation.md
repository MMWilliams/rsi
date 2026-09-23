# transfer/g6/10101/g5/p1

Run: `inheritance-20260916-v5`
Explanation script SHA-256: `a1d210cbb1cf305cc223e77af0f9efdae1e2fc0d90b7a44a6479bd0eddc51ad8`
Journal head at rendering: `bbc6485449f02b5943b57e8f061eac50cd73b0c60a403ca33628ba86146d5a79`
Journal events: 406 (proposed), 411 (resolved).
Resolution hash: `626ad34f64ea5a7531ef7da7a6dfd64e928ded592164be11151a4d578ca04344`

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

maximum_sampled_productivity_plus_mean_gain_plus_quarter_descendant_mean; lexical_name_tiebreak

Effect-table hash: `96ea4fa80c117d16cb8d22df8bb73e7da0c22bb3c058dd277e807f7a3ea900af`
RNG before/after: `c2a9eefddd16da831a2175c234aa0f9d240a9b753e3c38b4bf3dd3edd46da853` / `a607a5164548cb9b257ad3ba3607ba4ce178a6820f5331b0845337939ee1660d`

| Operator | Beta draw | Mean gain | Descendant mean | Combined score | Chosen |
|---|---:|---:|---:|---:|---|
| absolute_cost_up | 0.173429 | -0.017857 | 0.000000 | 0.155572 |  |
| match_cost_down | 0.254039 | -0.020833 | 0.062500 | 0.248831 | yes |
| match_cost_up | 0.069288 | 0.000000 | 0.000000 | 0.069288 |  |
| constant_cost_down | 0.233923 | 0.000000 | 0.000000 | 0.233923 |  |
| constant_cost_up | 0.017298 | -0.010417 | 0.000000 | 0.006882 |  |
| case_cost_down | 0.013953 | 0.000000 | 0.000000 | 0.013953 |  |
| case_cost_up | 0.005415 | 0.000000 | 0.000000 | 0.005415 |  |
| progress_weight_down | 0.030270 | -0.010417 | 0.000000 | 0.019853 |  |
| progress_weight_up | 0.036786 | 0.000000 | 0.000000 | 0.036786 |  |
| widening_down | 0.040690 | 0.000000 | 0.000000 | 0.040690 |  |
| widening_up | 0.213535 | 0.008929 | 0.062500 | 0.238088 |  |

Scores are selection heuristics, not calibrated probabilities of future improvement.

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
Evaluation events: 403 and 407; matched by both request hash and trajectory label.
Gained task IDs: 1c22fd36caf473a20c6d, ae69d8fd62c1b5b2f26c.
Lost task IDs: none.

Candidate evaluation cost record (logical counts; worker time excludes host grading):
```json
{
  "incidents": 0,
  "model_proposal_checks": 0,
  "oracle_string_executions": 256,
  "primitive_executions": 151184,
  "replay_batches": 1,
  "search_expansions": 3406,
  "wall_seconds": 0.40876779999234714,
  "worker_batches": 2
}
```

### Admission

Parent 8/16; candidate 9/16. Wins: 1; losses: 0.
Evaluation events: 408 and 409; matched by both request hash and trajectory label.
Gained task IDs: 1da94aa8d603c53d15a7.
Lost task IDs: none.

Candidate evaluation cost record (logical counts; worker time excludes host grading):
```json
{
  "incidents": 0,
  "model_proposal_checks": 0,
  "oracle_string_executions": 256,
  "primitive_executions": 147532,
  "replay_batches": 1,
  "search_expansions": 1956,
  "wall_seconds": 0.2818760999944061,
  "worker_batches": 2
}
```

## Statistics

```json
{
  "before": {
    "accepted": 1,
    "beneficial": 1,
    "descendant_gain_sum": 0.125,
    "descendant_trials": 2,
    "gain_sum": -0.125,
    "trials": 6
  },
  "after": {
    "accepted": 2,
    "beneficial": 2,
    "descendant_gain_sum": 0.125,
    "descendant_trials": 2,
    "gain_sum": 0.0,
    "trials": 7
  }
}
```

The complete-run audit separately checks these statistics and selection traces. A valid journal chain alone does not establish correctness.
