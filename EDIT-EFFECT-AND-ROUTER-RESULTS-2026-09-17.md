# Edit-effect feedback and evaluator combination

The confirmed E192 evaluator remains the best supported component. This
round tested whether an improver can value evaluator-training edits, and
whether two different evaluators can be combined. The learned router scored
better in aggregate on fresh tasks but failed its predeclared replication
gate. No child-improver growth is established.

## What an edit actually did

Two inspected source-target episodes each supplied 24 base feedback tasks,
48 candidate one-task training edits, and 96 separate target tasks. Exact
retraining found 19 positive and 9 negative top-choice edits in episode A;
23 positive and 12 negative in B. Mean effects were only +0.10 and +0.25
correct tasks per edit. Individual edit value is noisy.

A linear public-feature effect predictor trained on one episode did not
transfer top-choice gain to the other: cross-episode correlations were -0.009
and -0.046. It weakly predicted Brier improvements (0.268 and 0.322), but
selecting 7,000 source candidate labels with inherited Brier effects scored
87/192 across the two inspected targets versus 97/192 for source order.
Scrambled effect weights scored 86/192. An AUC-effect predictor also failed
to transfer (correlations -0.174 and -0.244). These are development results,
not fresh confirmations.

Directly replaying each child on the *other* episode's validation bank
transferred Brier effects (correlations 0.412 and 0.803) and pairwise AUC
effects (0.703 and 0.386). It did not transfer top-choice correctness effects
(-0.051 and -0.277). A smooth top-choice margin at fixed temperature 0.1
gave mixed results: one cross direction correlated 0.36 with current
correctness; the other only 0.07. Verified proxy gains alone would have
selected edits that missed or harmed the primary outcome.

## Sensor-gated seed-improver pilot

On an inspected 96-task admission / 96-task final split, a candidate
improver considered replacement, cumulative, and blended training updates
using 48, 96, or 192 new feedback tasks. Its fixed gate required at least
two more correct admission choices than E192. No update passed, so it kept
E192, scoring 48/96 on final. The hindsight best edit scored 49/96 and
several alternatives regressed. The gate avoided harmful promotions but did
not create a better evaluator in this pilot. This is development-only and
does not establish that the gate transfers.

## Pairwise evaluator and router

Random verified positive-negative candidate pairs, derived from E192's same
31,500 source labels, increased mean candidate AUC from roughly 0.71 to
0.79 on two inspected 192-task banks. Top-choice totals remained 201/384 for
E192 versus 200/384 for pairwise. Hard-pair-only training regressed sharply.
The two models made different choices on 279/384 tasks; an oracle choice
between their outputs would solve 237/384, a ceiling unavailable to a real
router.

A ridge router trained on 73 decisive tasks from the inspected banks chose
between E192 and pairwise using public candidate count and the models' top
probabilities and margins. Whole-episode development transfer scored 107
versus E192 102 in one direction and tied E192 99 in the other. The final
router was frozen before six new 32-task banks.

| Zero-query evaluator on fresh banks | Correct / 192 |
| --- | ---: |
| E192 classifier | 95 |
| Pairwise ranker | 95 |
| Equal-weight combination | 101 |
| **Learned router** | **102** |
| Higher-margin router | 95 |
| Deterministic random router | 94 |
| Oracle union of the two base decisions | 115 |

Learned-router minus E192 differences by bank were `[0, 5, 2, 1, -2, 1]`.
The six-bank resampling 95% interval for the mean difference was `[-0.5,
3.0]` tasks per bank. The router won four banks, tied one, and lost one; the
predeclared gate required five wins and a positive interval. It exceeded
equal-weight combination by only one task. It is a provisional evaluator
candidate, not a promoted replacement for E192. The 192-case reconstruction
audit passed at `runs/evaluator-router-transfer-20260917/audit.json`.

The router requires correct/incorrect feedback on the two selected programs
per training task: 663 distinct selected-program checks across the 384 old
tasks because the models selected the same program on 105 tasks. Earlier
research runs acquired much more data to inspect candidate reachability.
Fresh preparation used 31,086 common candidates and 75.7 seconds with eight
workers, separate from the verifier and prior component-training costs.

## Next decision

The current bottleneck is *top-choice edit utility*. Better global ranking or
probability error does not reliably make the highest-ranked program correct.
Keep the external oracle and a top-choice admission gate. The next edit type
should directly address the top incorrect candidates, with a cost-matched
control and fresh banks. Then test whether an inherited improver selects and
improves that edit procedure from the same starting system; a stronger
evaluator alone is not the requested recursive outcome.
