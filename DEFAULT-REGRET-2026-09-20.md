# Why improver growth stays out of reach: good defaults are already near-optimal

2026-09-20. Computed from audited rows of
`runs/region-acquisition-improver-transfer-20260920/`,
`runs/heterogeneous-ast-environment-20260920/` and
`runs/heterogeneous-ast-environment-rep2-20260920/`.

## The measurement

**Default regret** is the gap between an action space's oracle and the best
policy that requires *no verified history at all*: a rule a researcher can write
down from first principles before seeing any labels. It is the entire budget
available to any learner, including a perfect one.

It differs from fixed regret, measured in
`ACTION-SPACE-STATIONARITY-2026-09-20.md`. Fixed regret asks what conditioning on
the instance could buy over the best *constant*. Default regret asks what
*learning* could buy over the best *guess*. An environment can have large fixed
regret and near-zero default regret, and the heterogeneous environment does.

## The result

| action space | oracle | best zero-knowledge default | default regret | captured by default |
| --- | --- | --- | --- | --- |
| region purchase, transfer B | 390 | 369, buy the largest pools | **21** | 61% |
| region purchase, transfer C | 389 | 388, buy the largest pools | **1** | 98% |
| per-task routing, replication one | 244 | 227, trust the more confident model | **17** | 93% |
| per-task routing, replication two | 269 | 242, trust the more confident model | **27** | 90% |

Against a twelve-bank interval half-width of roughly 9 to 13, every one of these
budgets is at or inside the noise.

## The direct test

Per-task threshold routing was the most promising action space found: its
headroom over the best constant is +79 and +109, roughly double the per-bank
version, and a deployable label-free rule reaches most of it. An improver was
given the job of learning the routing threshold from verified history.

It learns something. Pooling twelve development banks beats the expected
single-bank draw by **+13** (interval +6 to +22) and **+12** (interval +4 to
+20), consistently across both replications.

It does not beat the zero-knowledge rule.

| | learned threshold | naive *t* = 0 | difference |
| --- | --- | --- | --- |
| replication one | 223 | **227** | **-4**, interval -12 to +4 |
| replication two | 244 | 242 | **+2**, interval -3 to +8 |

"Trust whichever specialist is more confident on this task" requires no history,
no labels and no improver, and the learned threshold does not beat it in either
replication.

## What this explains

The same shape has now appeared at four levels of action space, each roughly ten
times larger than the last:

| action space | total value | what a learner could add |
| --- | --- | --- |
| whole-bank policy menus | small | oracle selection +5, +8 |
| region purchase, budget 3 of 6 | +54, +44 over E0 | fixed regret +6, +12; default regret +21, +1 |
| per-bank action choice, 3 actions | +104, +92 over E0 | contextual value +22, +26, both crossing zero |
| per-task threshold routing | +165, +160 over E0 | default regret +17, +27; learned gain -4, +2 |

Enlarging the action space raised the total value by more than an order of
magnitude and left the *learnable* residual flat and inside the noise, every
time. The reason is consistent: in this benchmark a simple rule written without
any data captures 90 to 98 percent of what the best available policy achieves.

This subsumes the stationarity diagnosis rather than replacing it. Stationarity
explained why conditioning on the instance was worthless on i.i.d. banks.
Building a non-stationary environment fixed that: fixed regret rose from 2.9 to
between 38 and 83, and conditioning became worth +58 and +84. But the *rule* for
conditioning turned out to be guessable, so the improver still had nothing to
learn. Non-stationarity is necessary and not sufficient.

## The precondition this adds

An action space qualifies for an improver-growth test only if, in addition to
P2 (power) and P2b (non-stationarity):

**P2c, default regret.** The gap between the oracle and the best policy
expressible without any verified history must exceed +20 per 576 tasks. The
zero-knowledge default must be constructed adversarially: the strongest rule a
competent researcher would write before seeing labels, not a deliberately weak
one such as a single random draw or an uninformed constant.

Every "improver growth" result this project has produced, including the +80 in
replication one and the +13 and +12 here, was measured against a baseline weaker
than that. That is the single recurring methodological error across roughly forty
experiments, and it is now stated as a gate rather than rediscovered.

## A space that clears P2c and still fails

The seven-action per-task space (E0 plus the six region specialists, chosen per
task) is the first to clear P2c. Against the obvious default, "use your own
region's specialist", default regret is **+38** and **+51** per 576 tasks,
comfortably above the threshold.

It fails the next condition anyway. The cross-region matrix shows the own-region
specialist is best in **11 of 12 region cells**, so the residual is not
region-level structure that a table could hold; it is per task. And a selector
trained on one audited panel's public features, tested on the other, **loses** to
the default in both directions:

| direction | learned | own-region default | oracle | learned minus default |
| --- | --- | --- | --- | --- |
| transfer_b to transfer_c | 396 | 405 | 456 | **-9**, interval -19 to +1 |
| transfer_c to transfer_b | 381 | 399 | 437 | **-18**, interval -27 to -9 |

The +38 and +51 are task-level noise. No improver can grow on them, and this was
established without building one.

This adds a fourth condition, and the order matters because each is cheap and
each rejects spaces the previous one admits:

| condition | asks | fails when |
| --- | --- | --- |
| P2, power | is the oracle headroom above noise | menus of whole-bank policies |
| P2b, non-stationarity | does the best action vary by instance | i.i.d. banks |
| P2c, default regret | can a no-history rule be beaten | per-task confidence routing |
| **P2d, learnability** | does a held-out-fitted policy capture the residual | seven-action per-task |

Every action space this project has tested fails at least one of the four.

## What would satisfy it

An environment whose optimal policy is not guessable. Candidates, none tested:

- **Deceptive confidence.** Specialists whose confidence is systematically
  miscalibrated in a direction that differs by mechanism, so "trust the more
  confident" is actively wrong and the correction must be learned per mechanism.
- **Many actions with non-obvious applicability.** Enough specialists that no
  hand-written rule covers them, with applicability depending on interactions
  between public features rather than one dominant signal.
- **Interacting edits.** Actions whose value depends on which other actions were
  already installed, so the ordering must be learned from verified descendant
  effects and cannot be read off any single statistic.

Each must be screened for default regret *before* an improver is built for it,
which now costs a single cheap computation on opened rows.

## Limits

- Oracles use final labels and are upper bounds, not deployable policies.
- Default regret depends on which zero-knowledge rule is proposed. A weaker
  proposed default inflates it, which is exactly the error this document names,
  so the rule must be chosen adversarially and stated explicitly.
- These measurements cover four action spaces on one synthetic benchmark. They
  do not show that good defaults dominate in general, only that they do here.
- Nothing here retracts evaluator growth, which is replicated and audited and
  does not depend on default regret: building a better component is not the same
  as choosing among components.
