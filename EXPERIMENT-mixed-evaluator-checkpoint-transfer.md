# Mixed-mechanism evaluator checkpoint transfer: frozen protocol

Frozen before generating the transfer banks on 2026-09-17. This study tests
retained evaluator learning on fixed candidate pools. It does not by itself
test whether an improver can choose or improve the training procedure.

## Source and checkpoints

Development source: 192 inspected tasks, 64 each from stack, mutation, and
self-edit transition mechanisms. Each task has one public example and a pool
from two prespecified candidate sources at cap 128 per source. The source
labels mark candidates correct only when they pass all 15 disjoint scoring
examples. Four whole-task development folds showed E0 structural 36/192 and
cross-fitted new structural 92/192. The source is not transfer evidence.

`analysis/mixed-evaluator-checkpoints.json` freezes:

- E0: prior audited I0 structural weights from `seed-low-9000`.
- E48, E96, E192: the same logistic structural learner after the first 48,
  96, or 192 source tasks respectively. Task order cycles mechanisms.
- Scrambled192: same 192 task pools and per-task positive-label counts, with
  candidate labels deterministically shuffled within each task.

The structural representation has 175 visible-only features. A local bug fix
casts parsed Boolean nodes to integers for the numeric feature; it preserves
the old feature values on non-Boolean programs. All checkpoints use the same
feature code and candidate pools at transfer time.

## Transfer and controls

Six untouched banks, seeds 902203–902208, 32 tasks per bank, cycling the three
mechanisms, one visible example, eight unlabeled probe inputs, and 15 final
examples. Stack uses candidate sources V67/V70, mutation V70/V72, and
self-edit V70/V73; each source is capped at 128 before deduplication.

Primary decision: select the highest-probability candidate from the common
pool with zero oracle output queries. Compare all five checkpoints, shortest
program and first generated candidate on each identical pool. Freeze all
selection indices before opening final labels. Candidate reachability is
reported separately. Calibration error is secondary and computed per task;
ranking scores are logistic probabilities, but calibration should not be
inferred from selection accuracy alone.

Secondary decision: one fixed uniform-entropy probe chosen from eight input
options, one target-output query per task; each checkpoint selects its
highest-ranked candidate consistent with that answer. The probe is identical
for all checkpoints. This checks whether the learned ranker still contributes
after the same external feedback. It is not part of the primary gate.

## Growth screen

The primary retained-evaluator screen passes only if E192 beats E0 on at
least five of six banks, the six-bank resampling 95% interval for the paired
mean difference excludes zero in the positive direction, and E192 beats
Scrambled192 in aggregate. Report E48 and E96 to show the actual learning
curve; do not assert monotonic improvement if it is absent. Compare with the
strongest fixed no-query control before naming the best evaluator seed.

Report source candidate-label acquisition (7,304 / 15,140 / 31,500 labels
for E48/E96/E192), candidate generation and execution time, and transfer
inference cost. Source labels were obtained by many program executions, not
by a few output queries. The result is scoped to these synthetic mechanisms
and finite final examples. The local bank file is not independently access
controlled; saved predecision records and code-hash audit are the safeguard.
