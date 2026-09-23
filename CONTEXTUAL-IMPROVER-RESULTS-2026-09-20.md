# Contextual improver transfer, two replications, 2026-09-20

Protocol: `EXPERIMENT-contextual-improver-transfer.md`, predeclared before any
transfer label was opened.
Runs: `runs/heterogeneous-ast-environment-20260920/` and
`runs/heterogeneous-ast-environment-rep2-20260920/`.

## Headline

**Improver growth is not achieved.** G2 passed on replication one (+80,
interval +17 to +146) and failed on replication two (+26, interval -1 to +62).
The contextual gate G1 failed on both. Under this programme's own criterion,
which requires two independent passing replications, the result does not stand.

The two replications disagree because the gate is sensitive to which single
development bank the `initial` parent happens to hold: 46 in replication one,
near the bottom of the single-bank range, and 92 in replication two, which
equals the best constant outright. The history-size curve puts single-bank
parents between 46 and 104 with a mean of 75, so this was foreseeable and is a
defect in the gate rather than a property of the learner.

What did replicate is the environment. The Beta(0.4, 0.4) generator produced
fixed regret of +53 and +40 in replication one and +47 and +67 in replication
two, against +11 and +7 on the balanced controls. An environment in which
improver growth is *measurable* now exists and is audited; an improver that
reliably grows in it does not.

## Phase E: the environment, built and measured

The stationarity diagnosis said the previous environment could not express
improver growth: fixed regret of +6 and +12 per 576 tasks, with eleven banks of
experience worth +1 and -3. The new generator draws a per-bank familiar/shifted
AST share from Beta(0.4, 0.4). Measured on **generated**, not resampled, banks:

| panel | fixed regret | best constant | contextual - constant | share corr |
| --- | --- | --- | --- | --- |
| beta_dev | **+53** | shifted, +93 | +14 | 0.82 |
| beta_transfer | **+40** | familiar, +104 | +14 | 0.90 |
| balanced_control | **+11** | familiar, +87 | **-15** | 0.15 |

`p2b_satisfied: true`. The balanced control is the composition every prior run
used, and it lands at +11 with context actively harming by -15, which is the
predicted behaviour of a stationary environment.

Note that the best *constant* action flips between panels: shifted on
development, familiar on transfer. A policy that learned the development-optimal
constant and carried it over scores 46 on transfer.

Two corrections were needed while building this. `pools_for` requires
`route_for_generation`, since shifted tasks carry family `shifted_ast` which the
generator's arm map does not know. More importantly, the protocol's original
context feature was wrong: the familiar and shifted generators both emit Unicode
block 0x800, so the block carries no signal here, unlike the cross-family
studies where it recovers the family exactly. The context is instead the
label-free statistic the dual-specialist route already used, the fraction of a
bank's tasks where the familiar reranker is more confident than the shifted one.
Its correlation with the true share is 0.82 and 0.90 on the beta panels.

## Results on `beta_transfer`

| policy | correct over E0 |
| --- | --- |
| `parent_empty`, `always_e0` | 0 |
| `parent_initial` = `parent_duplicate` | 46 |
| `always_shifted` | 46 |
| `parent_scrambled` | 86 |
| `always_familiar`, the best constant | 104 |
| **`parent_later`** | **126** |
| per-bank hindsight, unavailable | 144 |

### G2, improver growth: **passed**

`later` minus `initial` is **+80**, six winning and one losing bank, interval
**+17 to +146**. `duplicate` holds twelve records carrying one bank's
information and scores exactly what `initial` scores, so the gain is information
and not record volume. `later` also beats `scrambled` by +40.

The mechanism is visible in the deployments. `initial` inherits only development
bank 908100, where shifted gained 8 and familiar 5, so it deploys **shifted on
all twelve transfer banks**. `later` inherits twelve banks spanning the share
range and deploys familiar on seven and shifted on five, tracking the true share
closely enough to leave regret of only 18 against the hindsight ceiling of 144.

### G1, contextual value: **failed**

`later` minus the best constant is **+22**, three winning and one losing bank,
interval **-16 to +62**. Conditioning on context is not shown to beat the best
single action chosen with hindsight.

## The falsification check did not behave as predicted

The protocol declared that the same comparison on `balanced_control` was
**expected not to pass**, and that a pass on beta together with a null on
balanced would be the evidence that the result came from non-stationarity.

It passed there too: `later` 86 against `initial` 57, gain **+29**, seven wins
and two losses, interval **+5 to +53**.

The reason is visible in the deployments and does not invalidate G2, but it does
narrow what G2 shows. On balanced banks `later` deploys familiar on nine of
twelve, and familiar *is* the better action there (166 against 136). So on the
control, `later`'s advantage is not contextual routing; it is simply that twelve
observations identify the better constant while `initial`'s single observation
locked onto the worse one.

That decomposes the +80 on `beta_transfer`:

| component | value | shown by |
| --- | --- | --- |
| identifying the right constant | **+58** (46 to 104) | also present on the control |
| conditioning on bank context | **+22** (104 to 126) | G1, interval crosses zero |

The honest claim is therefore **improver growth in the estimation sense**: more
verified history produced materially better deployments on untouched banks. The
stronger contextual claim is not established by this replication.

A gate design lesson follows, and it applies to the whole programme: G2 as
written can be passed by better constant estimation alone. A gate intended to
test contextual growth must compare against the best constant, as G1 does, not
only against a weaker parent.

## The history-size curve shrinks the effect from +80 to +51

`analysis/history-size-curve-20260920.json` deploys parents holding 1, 2, 3, 4,
6, 8, 10 and 12 development banks, averaging over every contiguous window of
each size, on the same untouched transfer panel.

| history | mean total | range over windows | vs best constant | share of hindsight |
| --- | --- | --- | --- | --- |
| 1 | **75.0** | 46 to 104 | -29 | 52% |
| 2 | 107.2 | 46 to 133 | +3 | 74% |
| 3 | 112.5 | 44 to 135 | +9 | 78% |
| 4 | 108.2 | 44 to 135 | +4 | 75% |
| 6 | 98.9 | 44 to 144 | -5 | 69% |
| 8 | 107.0 | 100 to 120 | +3 | 74% |
| 10 | 108.7 | 100 to 115 | +5 | 75% |
| 12 | **126.0** | single window | +22 | 88% |

Three corrections follow, and they matter more than the headline.

**The +80 overstates the effect.** The protocol fixed `initial` as the
lowest-seed development bank, which is a legitimate predeclared choice, but that
bank scored 46 against a single-bank mean of 75 and a range up to 104. Averaged
over every single-bank parent, going from one bank of history to twelve is worth
**+51**, not +80.

**The curve is not monotonic.** It rises to 112.5 at three banks, falls to 98.9
at six, and only reaches 126 with the full twelve. More verified history does
not reliably produce a better parent at every step; the nearest-share rule is
noisy in between.

**Most of the curve sits at the best constant.** Every history size from two to
ten lands between 98.9 and 112.5, against the best constant's 104. Only the full
twelve-bank history clears it by a margin, and G1 shows even that margin has an
interval crossing zero. This is the same picture the balanced control gave: what
extra history reliably buys here is the right constant, and contextual routing
is a smaller and less certain increment on top.

## Replication two: G2 **failed**. Growth is not reliable.

Seeds 909100 onward, no rule, threshold or control changed.
Run: `runs/heterogeneous-ast-environment-rep2-20260920/`.

Phase E held: fixed regret **+47** on dev and **+67** on transfer, against
**+7** on the balanced control. The environment behaved as designed.

The improver did not.

| policy | rep 2 beta_transfer | rep 2 balanced_control |
| --- | --- | --- |
| `parent_initial` = `parent_duplicate` | 92 | 92 |
| `always_familiar`, best constant | 92 | 92 |
| `parent_scrambled` | 88 | 67 |
| `always_shifted` | 82 | 57 |
| `parent_later` | **118** | **77** |
| per-bank hindsight | 159 | 99 |

- **G2 failed**: `later` minus `initial` is **+26**, three wins and one loss,
  interval **-1 to +62**, which crosses zero.
- **G1 failed**: identical figures, because `initial` and the best constant
  coincide here.
- On the balanced control, `later` was **worse** than `initial` by **-15**,
  interval -32 to 0. In replication two the stationarity falsification check
  behaved exactly as predicted; in replication one it did not.

### Why the two replications disagree

`initial` holds one development bank, and which bank that is decides the
comparison. In replication one it scored 46, near the bottom of the single-bank
range. In replication two it scored 92, which is exactly the best constant, so
there was almost nothing left for extra history to buy.

The history-size curve predicted this: single-bank parents span 46 to 104 with a
mean of 75. **G2's outcome depends on the luck of the initial parent's draw.**
That is a defect in the gate, not a property of the improver. A gate on
accumulated experience must average over initial draws, as the curve does, or
fix the baseline at the mean rather than at one predeclared seed.

Across both replications the beta-panel effect is +80 and +26. The direction is
consistent and the magnitude is not, and one of two intervals crosses zero.

## Status against the reliability criterion

Section 8 of `TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md` requires G2 and G3
each to pass on **two independent frozen replications** with passing audits.

**G2 passed once and failed once. Reliable improver growth is not achieved.**
G3, recursive child growth, was never run. The honest status of the programme is
unchanged on its central question: evaluator growth is replicated and audited;
improver growth is not established.

What this round did establish is narrower and still worth keeping. The reason
forty earlier gates failed was measured rather than guessed, an environment that
can express the result was built and confirmed on generated banks, and the first
gate pass was obtained and then correctly withdrawn under replication.

## Costs and audit

172,038 candidate labels checked across 1,728 generated tasks; 1,236 s
preparation. The independent audit regenerates every panel from its seeds and
share prior, rebuilds all pools, recomputes both candidate orders and every
action's verified top choice, then reconstructs each parent's per-bank
deployment from inherited records alone and recomputes fixed regret and all
gates with its own code.

## Limits

- One synthetic benchmark and one mechanism axis.
- The specialists are the frozen 2026-09-18 models, not retrained here, so their
  off-domain harm is inherited rather than designed.
- The environment was built *because* simulation predicted it would have
  measurable fixed regret. That makes G2 a fair test of whether extra history
  helps where context matters; it says nothing about how often real task
  distributions are non-stationary.
- `initial` is a single-observation parent, which is the weakest informative
  baseline. The +80 would shrink against a parent holding three or four banks,
  and that curve has not been measured.
- No child-improver test was run, so nothing here speaks to recursive growth.
