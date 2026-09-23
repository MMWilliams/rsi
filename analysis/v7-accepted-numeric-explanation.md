# Library change: transfer/numeric_pair/181/g1

Run: `library-inheritance-20260916-v7`. Semantic audit: **passed**.

This explanation reads recorded evidence; it performs no new search and does not establish a causal mechanism.

## Parent and proposal rule

Mode: `numeric_pair`. Parent stored library entries: 13 (the historical four-atom entry is ignored by search).
Parent development score: 9/16; admission score: 10/16.

Library candidates rank by visible compatibility, number of supporting solution certificates, fragment length, then lexical text. Numeric and frozen controls use their declared fixed proposals.
This generation added 8 fragment-certificate links from verified harvest solutions.
Visible ranking charged 274 primitive executions as an upper bound.

## Candidate outcomes

| Index | Kind | Development change | Admission change | Decision |
| --- | --- | ---: | ---: | --- |
| 0 | numeric | +0.000 pp | not evaluated | not_selected |
| 1 | numeric | +12.500 pp | +0.000 pp | development_gain_and_admission_nonregression |

Only the development winner gets the admission test. Acceptance requires positive development gain and no net admission regression.

## Proposal 0

`absolute_cost_down`

Candidate score: 9/16. Accepted: **False**.
Development wins: none.
Development losses: none.

Parameter changes: `{"absolute_cost": {"after": 0.65, "before": 1.0}}`.
Library additions: none.

Candidate evaluation request: `9323c4d56c9ca348f32b4b6230a00a88965627db7a38bf618e71df514158a3a8`.
Parent evaluation request: `6823fcdb306b84b1f261fa682687b4e6ee33737af18653e489da5c0eaecc762e`.
Candidate logical charges, including replay: `{"incidents": 0, "model_proposal_checks": 0, "oracle_string_executions": 256, "primitive_executions": 152188, "replay_batches": 1, "search_expansions": 2466, "wall_seconds": 0.4075721999979578, "worker_batches": 2}`.

## Proposal 1

`absolute_cost_up`

Candidate score: 11/16. Accepted: **True**.
Development wins: ['b11d8cd5108c25c39648', '873cc29f385216c11541'].
Development losses: none.
Admission wins: none.
Admission losses: none.

Parameter changes: `{"absolute_cost": {"after": 1.4, "before": 1.0}}`.
Library additions: none.

Candidate evaluation request: `795124984abfe2a53c8534d8b493293024c1e96e447eb6d39c37e5a2362aa165`.
Parent evaluation request: `6823fcdb306b84b1f261fa682687b4e6ee33737af18653e489da5c0eaecc762e`.
Candidate logical charges, including replay: `{"incidents": 0, "model_proposal_checks": 0, "oracle_string_executions": 256, "primitive_executions": 152188, "replay_batches": 1, "search_expansions": 2470, "wall_seconds": 0.43389919999754056, "worker_batches": 2}`.

## Provenance

Journal: 2404 events; final hash `ac2da801b3e6785bd9d40df59079a0dcaf2ff8bd2b73861098ca95e2c5fcab8f`.
Proposal event: 279 / `1a03a65d2edd5abe2df065d3a421c96fb8498a5bb95286dfcdc16bdc1cd6a620`.
Resolution event: 285 / `bfb8a0abdd642ca882edf6e57cf092d1224171e53ccd0229a909df624db57fba`.
Memory: `7fa08592ffebd86f245f01bacc04b259f0269497f287e2d394b9d92b610bee2d`.
Explanation script: `b629437e5734b8fc866dd1d138d74c811768ae42d80e23747e5e8972b50472d4`.

Finite admission examples can miss regressions. Hashes detect changes but do not authenticate the host. Artifact gains alone do not demonstrate a better improver or RSI.
