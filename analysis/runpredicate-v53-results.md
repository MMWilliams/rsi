# V53 run-predicate boundary transfer

Status: audited two-seed result. V53 removes the explicit transition primitive from V52's evaluation path. It searches over generic `Slice(run(predicate, ordinal, side), run(predicate, ordinal, side))` endpoints, where the run predicates are inferred from the visible training tasks.

| Seed | Fixed-DSL baseline final | Run-predicate final | Baseline admission | Run-predicate admission | Baseline development | Run-predicate development |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026091906 | 24/24 | 24/24 | 20/24 | 24/24 | 21/24 | 24/24 |
| 2026091907 | 23/24 | 24/24 | 23/24 | 24/24 | 20/24 | 24/24 |

The run-predicate arm selected `run_c10` on both seeds and verified all 48 delimiter-training tasks on each seed. It reached 48/48 final tasks pooled, versus 47/48 for the fixed baseline. The main signal is therefore not a final-score jump on this small bank, but a repeated admission/development improvement and a successful transfer using generic run endpoints rather than a named transition operator.

The result narrows, but does not remove, the main limitation. The predicate vocabulary (`alpha`, `digit`, `space`, `punct`, `upper`, `lower`, `alnum`) is still researcher-bounded, and the domains are synthetic. The next test should allow predicates to be induced from character partitions or learned classifiers, with the predicate inventory frozen before final evaluation.

Both independent audits passed. Each replayed 288 evaluation rows and checked 20 sealed artifacts.

Artifacts: `runs/runpredicate-v53-20260918/` and `runs/runpredicate-v53-20260919-seed07/`.
