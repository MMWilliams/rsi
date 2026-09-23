# V25 generator-derived Bayesian prior

Status: audited exploratory gain. This experiment tests whether a passive program prior derived from the synthetic task generator can resolve ambiguity that cost ranking leaves in the candidate pool.

## Protocol

The candidate grammar and visible examples were fixed before evaluation. The control selected the first visible-consistent candidate from the enumerator. The Bayesian arm selected the candidate with the highest log probability under a prior matched to the generator's atom-count, constant, substring, match-position, and case probabilities. Development and admission splits were used only for the pre-registered non-regression gate; the fresh final split was scored after selection. No hidden oracle feedback was supplied during solving.

## Results

| Replication | Arm | Development | Admission | Fresh final |
| --- | --- | ---: | ---: | ---: |
| V25b | Cost ranking | 18/24 | 20/24 | 16/24 |
| V25b | Bayesian prior | 16/24 | 20/24 | 17/24 |
| V25c | Cost ranking | 18/24 | 18/24 | 17/24 |
| V25c | Bayesian prior | 17/24 | 19/24 | 18/24 |

The Bayesian arm was retained on both replications. It improved the final result by one task on each independent fresh bank: 33/48 combined for the control versus 35/48 for the Bayesian prior (+2 tasks, +4.17 percentage points). The development scores were not uniformly better, so the result is a selection/inductive-bias gain rather than evidence that the prior learned from development.

## Audit and interpretation

Both sealed archives passed independent replay. Each audit re-created the fresh bank, recomputed all candidate pools and prior scores, checked the admission gate, replayed 144 staged evaluations, and verified 19 sealed artifacts. The gain is meaningful but bounded: the prior is hand-specified, the DSL and grammar are fixed, banks are small, and grading uses a same-host hidden oracle. This is not proof of recursive self-improvement or RSI.

The strongest current interpretation is that a model of the task-generation distribution can improve passive hypothesis selection modestly. A next test should learn or evolve the prior itself under a sealed admission gate, while keeping the grammar and final bank untouched.

Artifacts: `runs/bayesian-prior-v25b-20260917/` and `runs/bayesian-prior-v25c-20260917/`.
