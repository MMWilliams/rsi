# Why improver growth has been unmeasurable: the environment is stationary

2026-09-20. Computed from the audited per-bank rows of
`runs/region-acquisition-improver-transfer-20260920/` (audit passed: 1,440 tasks
regenerated from seeds, 135,728 candidate labels rechecked, zero failures).
Source: `analysis/action-space-stationarity-20260920.json`.

## The result

| quantity | transfer B | transfer C |
| --- | --- | --- |
| best fixed region set, value over E0 | +54 | +44 |
| per-bank hindsight value, perfect context | +60 | +56 |
| **fixed regret: the whole contextual budget** | **+6** | **+12** |
| distinct per-bank optimal sets | 6 of 12 | 6 of 12 |
| banks where the global optimum is also the bank optimum | 2 | 1 |
| policy fitted on 1 bank, scored on the rest | +53 | +37 |
| policy fitted on 11 banks, scored on the held-out bank | +54 | +34 |
| **value of accumulated experience** | **+1**, interval 0 to +3 | **-3**, interval -11 to +5 |

## What it means

Two facts have to be held together.

**The optimal action does vary by bank.** Six distinct region sets are optimal
across twelve banks, and the globally best set is the bank-level optimum on only
two banks of twelve on B and one of twelve on C. On its face that looks like
context worth learning.

**But the variation is noise, not structure.** Per-bank region gains are
integers between -2 and +4 on 48-task banks. With signal that small, which
region happens to win a given bank is mostly sampling variation. The proof is
the last two rows: a policy fitted on a *single* bank scores +53 against a
policy fitted on *eleven* banks scoring +54. Eleven times the experience is
worth one correct task, with an interval touching zero, and on transfer C more
experience is actively worse.

The ceiling is equally clear. Fixed regret, +6 and +12, is the entire value
available to any context-conditioned policy, including an unachievable one with
perfect per-bank hindsight. Against a twelve-bank interval half-width of about
9, that ceiling is inside the noise it would have to beat.

## Why this explains roughly forty failed gates

The benchmark draws every bank i.i.d. from a fixed family mix. Region repayment
therefore has no dependence on any observable bank property: ast has mean rank
0.58 and transform 1.50 on transfer C, and those ranks are stable because
nothing about a bank makes one region pay more than another. When instances are
i.i.d., the optimal action is a constant, one observation estimates it almost as
well as twenty, and the residual per-bank variation is sampling noise that no
learner can predict.

Every improver test in this project has been asked to beat a constant policy in
an environment whose optimal policy *is* constant. The failures were not
evidence about the learners. They were a property of the task distribution, and
it was invisible because no study had measured fixed regret.

This subsumes the earlier action-space diagnosis. Enlarging the action space
from whole-bank policies (oracle +5, +8) to region purchases (oracle +54, +44)
multiplied the total available value tenfold and left the *learnable* fraction
unchanged at +1 to +12, because what grew was the value of the constant, not the
value of conditioning.

Note also the direction of scale. Larger banks would shrink per-bank noise and
therefore shrink fixed regret toward zero. In a stationary environment, making
the measurement more precise makes improver growth *less* measurable, not more.
No sample-size fix exists.

## What follows

Improver growth cannot be demonstrated on this task distribution, at any action
space, by any learner. The programme's next move is not another improver design
and not another action space. It is an environment whose optimal action genuinely
depends on observable instance properties.

The requirement is precise, and it is now a precondition in
`TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md`:

1. **Non-stationarity.** Banks must be drawn with varying generator parameters,
   family mixes or difficulty, such that the best construction differs by bank.
2. **Learnability.** That dependence must be predictable from public
   instance features, verified by showing a context-conditioned policy fitted on
   held-out banks beats the best constant policy.
3. **Signal above noise.** Measured fixed regret must exceed +20 per 576 tasks,
   twice the twelve-bank interval half-width, before any improver gate runs.

Fixed regret is cheap to compute and must be reported for every candidate
environment *before* any improver is built for it. An environment that fails
condition 3 is rejected without running an improver at all.

## Limits

- Hindsight sets use final labels and are not deployable policies; they are
  upper bounds.
- This measures the region-purchase action space on this benchmark. A different
  action space on the same i.i.d. banks would need its own fixed-regret number,
  but the i.i.d. argument above predicts the same outcome.
- The one-shot arm uses the first remaining seed as its single sample rather than
  averaging over all choices of single bank, so it is one draw, not an
  expectation. The eleven-bank arm is a proper leave-one-out.
- Nothing here contradicts the evaluator results. Evaluator growth passed its
  gate on fresh banks (+49/576, twelve of twelve, interval +37 to +62) and is
  unaffected: building better components does not require non-stationarity.
