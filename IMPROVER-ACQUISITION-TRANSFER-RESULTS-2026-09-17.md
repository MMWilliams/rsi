# Same-base improver acquisition transfer

The feedback-acquisition rule chosen on development data **failed** its fresh
transfer test. The evaluator improvement from training remains real, but
these data do not identify a reliably superior 7,000-label improver or show
that updating the improver during the loop helps.

## Matched acquisition test

The frozen protocol is `EXPERIMENT-improver-acquisition-transfer.md`. All
arms started from the same E0 structural evaluator, saw the same 192 public
source task pools, and spent exactly 7,000 candidate-correctness labels.
Each selected candidate was checked on 15 source examples. All child
evaluators used the same logistic structural learner. Child weights and
choices were saved before six new 32-task target banks were scored. The
target banks had 191/192 reachable tasks.

| Acquisition rule / reference | Correct / 192 target tasks | New source labels |
| --- | ---: | ---: |
| E0, no update | 36 | 0 |
| Source order | 95 | 7,000 |
| Deterministic random task order | 96 | 7,000 |
| Smallest candidate pools first | 89 | 7,000 |
| E0 uncertainty | 82 | 7,000 |
| **E0 low-confidence task ranking** | **83** | 7,000 |
| Three-stage low-confidence with retraining | 97 | 7,000 |
| Historical E192 reference | 102 | 31,500 earlier source labels |

The prespecified low-confidence-minus-order differences by bank were
`[-3, -3, 2, -1, -1, -6]`, minus 12 in aggregate. The six-bank resampling
95% interval for the mean paired difference was `[-4, 0]` tasks per bank.
Low-confidence won one bank and failed the primary gate. It also lost to
random and small-pool was not enough to explain the result. The development
score had favored low-confidence 97 versus order 91/192 on a different
source-target pair; that advantage did not transfer.

The iterative rule scored two above source order and one above random, with
bank differences versus order `[0, 0, 1, 1, 2, -2]`. Its mean-difference
interval `[-0.67, 1.17]` includes zero. It did not pass a positive-growth
screen. E192 is a useful evaluator reference, but its historical 31,500
labels make it an unequal-cost control here.

## What changed the next design

Low-confidence selected 58 source tasks, including 23 mutation and 20
self-edit tasks, and opened 2,483 positive candidate labels. Source order
selected 47 tasks, nearly balanced by mechanism, with 1,638 positive labels.
More positive examples and more tasks did not produce a better child. The
failure is consistent with a need to measure *discriminative training value*
for ranking candidates: whether feedback distinguishes a correct program
from plausible wrong ones on later tasks. It is not proof that positive-label
prevalence caused the regression. A development-only public-context balanced
low-confidence rule tied source order and supplied no stronger candidate for
immediate confirmation.

All 192 source tasks, 192 target tasks, selected source labels, child weights,
target choices, and final outcomes passed reconstruction audit at
`runs/improver-acquisition-transfer-20260917/audit.json`. Each arm was charged
7,000 labels even where actual oracle computations were shared; 21,160
unique candidate labels were executed across arms. Preparation took 134.0
seconds of wall time for shared candidate generation, source training and
target predictions, plus the later scoring and audit work. The task domain
and finite-example oracle remain synthetic and locally controlled.

The best *supported evaluator* remains E192 for this distribution. The best
7,000-label acquisition rule in this one fresh test was iterative
low-confidence by one task over random, but the difference is too small and
unstable to promote it as a seed improver. Next, estimate each source task's
effect on future candidate ranking using disjoint development tasks, then
train and test an acquisition policy on new source-target episodes. A later
parent must still create a better child improver from an identical base on a
second untouched bank to establish recursive improver growth.
