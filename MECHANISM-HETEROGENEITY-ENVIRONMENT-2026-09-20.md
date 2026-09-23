# An environment where improver growth is measurable, 2026-09-20

Resampling simulations on audited rows. Nothing generated, no policy frozen.
Sources: `analysis/heterogeneous-regret-simulation-20260920.json`,
`analysis/mechanism-regret-simulation-20260920.json`.

## The question

`ACTION-SPACE-STATIONARITY-2026-09-20.md` established that the current benchmark
cannot support an improver-growth result: fixed regret, the entire value
available to a perfectly context-conditioned policy over the best constant
policy, is only +6 and +12 per 576 tasks, and eleven banks of experience beat
one bank by +1 and -3. P2b in the technical design therefore requires a
candidate environment to show fixed regret above +20 before any improver is
built for it.

This measures two candidate environments against that bar, using audited
per-task labels so every label is real and only bank composition is synthetic.

## Candidate 1: vary the family mix. Fails.

Resampling the audited region-acquisition rows into banks with varying family
mixes, budget 3 of 6 regions:

| environment | fixed regret | contextual - constant |
| --- | --- | --- |
| iid, equal mix (control) | 12.2 | -7.1 |
| Dirichlet(0.35) mixes | 14.7 | -1.6 |
| split into two disjoint region triples | 16.8 | +5.3 |

The control reproduces the +6 to +12 measured on real banks, so the simulation
is calibrated. But even the adversarial `split`, where two disjoint triples mean
no budget-3 purchase can serve both bank types, reaches only 16.8.

The reason is structural. Every region specialist *helps*, by between 0 and +25
per 96 tasks, and none of them harms. When all actions have the same sign,
reweighting which tasks appear cannot make the wrong action costly. It only
changes how much the right one earns.

## Candidate 2: vary the mechanism. Clears the bar by 2 to 4x.

The familiar/shifted AST split does have actions that harm. Measured on the
audited dual-specialist transfer, per 96 tasks, against E0:

| | familiar tasks | shifted tasks |
| --- | --- | --- |
| familiar model | **+35** | -2 |
| shifted model | -14 | **+26** |

The sign flips. Deploying the shifted model on familiar tasks costs 14 correct
choices. Resampling those rows into banks whose familiar share varies *between*
banks, with a budget of one model:

| environment | fixed regret (p10, p90) | contextual - constant (p10, p90) | context wins |
| --- | --- | --- | --- |
| **balanced, 50/50 every bank** | **2.9** (0, 7) | -0.8 (-5, +2) | 14% |
| drifting share 0 to 1 | 38.4 (29, 49) | +30.9 (+14, +44) | 97% |
| Beta(0.4, 0.4) shares | 48.3 (23, 71) | +41.4 (+11, +67) | 95% |
| split, all-familiar or all-shifted | 83.4 (75, 93) | +83.3 (+75, +93) | 100% |

## The finding

**`balanced` is the original dual-specialist run's design, and its fixed regret
is 2.9.** Every bank was composed identically at 50/50, so the best model was
the same on every bank and there was nothing to condition on. That run's
improver-growth failure, like the thirty-nine before it, was a property of the
bank composition rather than of the learner.

Changing nothing but the *between-bank* variation of a single public proportion
lifts fixed regret from 2.9 to between 38 and 83, and a deliberately weak
nearest-neighbour learner on that public proportion captures most of it, winning
in 95 to 100 percent of draws.

Two conditions had to hold together, and the failed candidate isolates them:

1. **Actions that harm off-context.** Family-mix heterogeneity failed because
   every region specialist helps. Mechanism heterogeneity works because the
   wrong model costs -14.
2. **Between-bank variation, not within-bank difficulty.** `balanced` banks are
   just as hard as `split` banks and contain exactly the same task pool; the
   best constant policy scores 98.4 and 99.7 respectively. Only the variance of
   the optimal action differs.

## What this authorizes

Phase E of `TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md` now has a concrete
specification. The generator draws a per-bank familiar/shifted share from
Beta(0.4, 0.4) or a drifting schedule, both of which clear P2b with room, and
exposes that share only through public task features, as the existing Unicode
block already does.

`split` is not recommended despite the largest regret: all-or-nothing banks make
the decision trivially inferable from one task, which tests detection rather
than accumulated experience. `beta` is the realistic choice and still delivers
48.3.

Before any improver is built on it, the real generator must reproduce these
numbers on generated rather than resampled banks. The simulation is evidence
that the compute is worth spending, not a substitute for spending it.

## Limits

- Rows are resampled with replacement from audited tasks, so bank composition is
  synthetic while every label is real. A real generator will not reproduce these
  values exactly.
- Both specialists were trained before this simulation, on the current source
  panels. A real heterogeneous environment would retrain them, and their
  off-domain harm could change.
- The contextual arm is nearest-neighbour on a single public proportion, chosen
  to be weak so that learnability is not overstated. It is not the improver.
- An earlier version of this simulation reported bootstrap intervals computed by
  passing 200 across-draw totals to a helper that bootstraps sums of paired
  per-bank differences; those brackets were inflated by roughly 200x and have
  been replaced with percentiles and a win rate.
- Fixed regret bounds what *any* contextual policy could gain. It does not show
  that a parent with more history will capture it; that is the frozen test.
