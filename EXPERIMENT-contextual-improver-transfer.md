# Contextual improver transfer on the heterogeneous environment

Predeclared 2026-09-20, before any label on the transfer panel is opened.

## Precondition

This protocol runs only if Phase E reports `p2b_satisfied`: fixed regret above
+20 on both beta panels of `runs/heterogeneous-ast-environment-20260920/`, and
at or below +20 on the balanced control. If the balanced control also clears
+20, the environment is not doing what the simulation predicted and this
protocol is void.

Rationale in `ACTION-SPACE-STATIONARITY-2026-09-20.md` and
`MECHANISM-HETEROGENEITY-ENVIRONMENT-2026-09-20.md`. On i.i.d. banks the optimal
action is a constant and no learner can show growth; that is why the previous
forty gates failed.

## The decision under test

Per bank, deploy exactly one candidate reranker from
{`e0`, `familiar`, `shifted`}. The choice is made before any final label on that
bank exists.

The only context available is **label-free model confidence**: for each task,
the top-candidate probability of the familiar reranker and of the shifted
reranker. The bank's public statistic is the fraction of its tasks where the
familiar reranker is the more confident of the two. The familiar and shifted
generators share Unicode block 0x800, so the block carries no signal and this
confidence statistic is the whole of the context. The true familiar share is
recorded for diagnosis and is never available to any policy.

## Improver state and selection rule

A parent holds records `(public_share, action, realized_gain_over_e0)` from
banks it has observed on the development panel. Its rule, identical for every
parent:

1. If it holds no records, deploy the declared default `e0`.
2. Otherwise, find the observed bank whose `public_share` is nearest to the new
   bank's, and deploy the action with the highest realized gain on that bank.
   Ties by action name ascending.

This is deliberately the weakest sensible learner. It has no capacity to fit
anything the records do not contain, so any advantage of a later parent comes
from holding more of the share-to-action mapping, not from a better model class.

## Parents

All parents share the same frozen base, the same three actions, the same rule,
and the same transfer panel.

| parent | inherited records |
| --- | --- |
| `initial` | the single development bank with the lowest seed |
| `later` | all twelve development banks |
| `duplicate` | the initial bank's record repeated twelve times |
| `scrambled` | all twelve, with realized gains permuted across banks |
| `empty` | none; deploys the declared default `e0` |

`duplicate` carries `later`'s record count and `initial`'s information. It is
the control that carries the claim.

Fixed controls: `always_e0`, `always_familiar`, `always_shifted`, and
`best_constant`, the single action with the highest total gain on the transfer
panel, which uses final labels and is therefore an unavailable reference rather
than a policy. Unavailable ceiling: `per_bank_hindsight`.

## Panels

Frozen in `runs/heterogeneous-ast-environment-20260920/` before this file was
written, from seeds never used elsewhere.

- `beta_dev`, seeds 908100-908111: the parents' observation panel.
- `beta_transfer`, seeds 908200-908211: the transfer panel, never observed.
- `balanced_control`, seeds 908300-908311: the stationarity control.

## Endpoints and gates

Correct zero-query top choices per 576 tasks, paired at bank level, with the
exact bank-bootstrap interval used throughout this project.

- **G1, contextual value.** `later` beats `best_constant` on `beta_transfer`.
  Pass: gain > 0 and interval excludes zero. This is the first test in the
  programme of whether conditioning on instance context is worth anything at
  all; every prior environment made it worthless by construction.
- **G2, improver growth.** `later` beats `initial` on `beta_transfer`. Pass
  requires all of: gain >= +6; at most 4 of 12 losing banks; interval excludes
  zero; and `later` >= `duplicate`.
- **G3, stationarity control.** On `balanced_control`, `later` minus `initial`
  is reported and is **expected not to pass** G2's thresholds. A pass on
  `beta_transfer` together with a null on `balanced_control` is the evidence
  that the result comes from environment non-stationarity and not from the
  learner having been given a better rule.

G1 and G2 are separate claims. G3 is a falsification check on the diagnosis, not
a growth claim.

## Secondary, reported but not gated

- Correlation between the public confidence share and the true familiar share.
- Each parent's regret against `per_bank_hindsight`.
- Per-bank chosen action for every parent, so every decision is reconstructible.
- Candidate labels checked and candidates rescored.

## Declared limits

- One synthetic string/program benchmark, and one mechanism axis.
- The specialists are the frozen 2026-09-18 models and were not retrained for
  this environment, so their off-domain harm is inherited, not designed.
- The environment was chosen *because* simulation said it would have measurable
  fixed regret. That makes G2 a fair test of whether extra history helps in an
  environment where context matters. It is not evidence about how often real
  task distributions are non-stationary.
- A G2 pass shows this improver used more verified history to make better
  contextual deployments. It does not by itself show recursive self-improvement;
  the child-improver test is separate and not run here.
