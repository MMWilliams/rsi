# Mixed-mechanism evaluator checkpoint transfer

The retained structural evaluator **passed the predeclared growth screen** on
six fresh banks. It selected better programs from identical candidate pools
without an oracle output query at inference time. This is a scoped evaluator
learning result. It does not establish an improved improver or recursive
intelligence growth.

## Fixed-pool test

The protocol is `EXPERIMENT-mixed-evaluator-checkpoint-transfer.md`. Source
feedback came from 192 previously inspected tasks across stack, mutation, and
self-edit mechanisms. Each task had one public example and a common pool from
two fixed generators capped at 128 candidates each. The evaluator's structural
model was trained on verifier labels for candidate programs. E48, E96, and
E192 use the first 48, 96, or 192 source tasks. Scrambled192 preserves each
task's number of correct candidates but shuffles their labels. The final six
32-task banks were generated after the checkpoints and comparison were frozen.
They contained 32,670 candidate programs; 191/192 tasks had at least one
candidate correct on all 15 final examples.

| Zero-query evaluator | Correct / 192 |
| --- | ---: |
| E0 prior structural model | 36 |
| E48 | 90 |
| E96 | 89 |
| **E192** | **99** |
| Scrambled192 | 72 |
| First generated candidate | 54 |
| Shortest program | 58 |

E192 minus E0 by bank was `[12, 13, 8, 14, 7, 9]`: positive in all six.
An exact six-bank resampling 95% percentile interval for the mean gain was
`[8.5, 12.5]` tasks per 32-task bank. E192 was correct on 76 tasks where E0
was wrong; E0 was correct on 13 where E192 was wrong. E192 exceeded the
scrambled-label control by 27 tasks, with bank differences `[3, 8, 0, 6, 6,
4]` and a mean-gain interval `[2.33, 6.33]`. It also exceeded both simple
fixed candidate rules. The prespecified growth screen passed.

The trajectory was not monotonic: E48 scored 90, E96 89, and E192 99.
Additional labels improved probability error steadily, but more feedback did
not produce a strictly increasing top-choice score at every checkpoint.
By mechanism, E192 scored 32/66 stack, 38/66 mutation, and 29/60 self-edit,
versus E0's 6, 10, and 20 respectively. The result is distributed across all
three tested mechanisms.

## Evaluation quality and integration

The mean per-task candidate Brier error fell from 0.549 for E0 to 0.175 for
E192; the shuffled-label control scored 0.189. These are candidate-level
probability estimates averaged by task, separate from top-choice accuracy.

With the **same** entropy-selected probe and one oracle output per task,
E192 selected a correct candidate on 160/192 versus E0's 115/192. It won on
all six banks, with paired bank differences `[10, 8, 8, 11, 3, 5]`. Thus the
learned evaluator still contributes after identical external feedback. This
secondary result does not compare alternative query policies.

## Audit, cost, and limits

`runs/mixed-evaluator-transfer-20260917/audit.json` passed all 192 cases. It
regenerated banks, checked visible candidate fit, rebuilt structural features
and all frozen choices, recomputed the common probe, and rescored final
labels. Decisions and model hashes were saved before the separate score
stage. The local files lack an independent host access-control boundary.

The E48/E96/E192 checkpoints consumed 7,304 / 15,140 / 31,500 source
candidate-correctness labels. Each label required testing a program on 15
examples. Source generation and labeling took 123.4 seconds of wall time in
the successful source run. Transfer preparation took 110.4 seconds with eight
workers; predicting outputs for the common probe options added 261,360
candidate executions. These preparation costs are shared across checkpoints,
while E192 bears the largest training acquisition cost. Lower error and higher
accuracy are measured at equal *inference* candidate pools and query budget,
not equal lifetime compute.

The final criterion is correctness on 15 generated examples, not universal
program equivalence. The task mechanisms and candidate generators are
researcher-built. The gain shows retained adaptation to this three-family
distribution; it does not prove transfer to unrelated research, security,
social-good, or policy work.

**Next:** use E192 as a supported evaluator component in a same-base
improver study. The improver must decide which feedback or evaluator edit to
apply, pay for that acquisition, and create a stronger evaluator or child
improver on new banks than a fixed training schedule. Keep E192 as a control;
do not promote it to a seed *improver* on this evidence alone.
