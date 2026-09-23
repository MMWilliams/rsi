# Construction-improver growth, confirmed on frozen banks, 2026-09-21

> **WITHDRAWN 2026-09-21 after the capacity-matched audit.** The E1 and E3 gates below were run
> against a pooled baseline with one quarter of the built system's leaf
> capacity, and the router was fitted on in-sample specialist views. With the
> router fitted out of fold and a single pooled model given matched capacity
> (60 leaves), the built system **loses by 50 and 36** at 24 history banks and
> E3 is negative or crosses zero against every baseline. The advantage this
> document reported was capacity, plus router leakage in replication one. E2
> alone survives, and E2 alone means "more data helps", which the pooled model
> shows too. The numbers below are retained as the record; the withdrawal
> section at the end has the audit. Source: `runs/*/oof_audit.json`.

Protocol: `EXPERIMENT-construction-improver-confirmation.md`, hashed before any
bank for either replication existed.
Runs: `runs/construction-improver-confirmation-20260921/` and
`runs/construction-improver-confirmation-rep2-20260921/`.

## What makes this the purer claim

The earlier confirmed result (`COMPLEXITY-IMPROVER-RESULTS-2026-09-21.md`)
tested an improver that **routes** among four specialists trained once, outside
the experiment, on opened panels. Two purity gaps followed: the components were
not part of the evidence, and "improvement" meant selection rather than
construction.

Here the improver receives verified history banks and nothing else. It computes
the latent complexity partition from its own labels, trains one specialist per
bin, trains a pooled model, fits its own router, and deploys. No model,
partition, router or label is inherited.

The baseline is the strongest free alternative: **one pooled model trained on
exactly the same history**, identical data, labels and compute, with no
partition and no router. That is what a researcher would build without knowing
the partition matters.

## Results

Correct zero-query top choices per 576 tasks, expected over strided windows.

| history banks | rep 1 built | rep 1 pooled | rep 2 built | rep 2 pooled |
| --- | --- | --- | --- | --- |
| 4 | 310.8 | 307.8 | 309.7 | 302.7 |
| 8 | 328.2 | 320.8 | 334.2 | 321.2 |
| 16 | 344.7 | 323.8 | **362.7** | 326.3 |
| 24 | **357.0** | 328.0 | 358.0 | 332.0 |

| gate | rep 1 | rep 2 |
| --- | --- | --- |
| **E1** construction beats pooling | **+29**, 9w/1l, interval **+12 to +50** | **+26**, 10w/1l, interval **+5 to +46** |
| **E2** construction growth | **+45**, 12w/0l, interval **+27 to +67** | **+49**, 12w/0l, interval **+37 to +62** |
| **E3** growth exceeds data volume | **+26.0**, 9w/3l, interval **+7.8 to +49.0** | **+19.0**, 10w/1l, interval **+0.2 to +38.3** (exact interval on rounded contributions **0 to +38**) |
| **E4** monotone (reported, not gated) | yes | **no** |

**E1, E2 and E3 pass on both replications**, which is the predeclared reporting
rule.

## E3 is the gate that carries the claim

Pooling the same data also improves as history grows, by +20.2 and +29.3. That
is just more data helping, and it is exactly what an improver-growth result can
be mistaken for. Construction grows +46.2 and +48.3, so the margin attributable
to the improver rather than to data volume is **+26.0 and +19.0**.

E3 is one estimand: per transfer bank, (built at 24 minus built at 4) minus
(pooled at 24 minus pooled at 4), summed, with a paired bootstrap interval over
banks. On that interval **replication two touches zero** (bootstrap lower bound
+0.2; exact enumeration on rounded contributions, lower bound 0). Significance
of E2 and of pooled growth separately did not establish significance of their
difference. The honest reading is that E3 is clean in replication one and
marginal in replication two. Per-bank contributions and both intervals are in
`analysis/e3-single-estimand-20260921.json`.

**Correction record.** The frozen `results.json` rounded each per-bank
difference to an integer before summing, separately for E2 and for pooled
growth. That produced 45 and 21 (replication one) and 49 and 29 (replication
two) where the unrounded values are 46.2, 20.2, 48.3 and 29.3, and E3 margins
of 24 and 20 where the single-estimand values are 26.0 and 19.0. E1 was
unaffected. The rounding existed to keep the exact-enumeration interval
tractable; the corrected analysis reports a percentile bootstrap on unrounded
contributions alongside the exact interval on rounded ones.

The routing experiment could not make this comparison at all, because its
components were fixed before the experiment began. It is the single strongest
reason to prefer this result over that one.

The advantage also widens with history rather than sitting at a constant offset:
+3, +8, +20, +29 in replication one and +7, +14, +37, +26 in replication two.

## The same runs give the purer verifier-growth claim

The evaluator-growth result on record (+49/576) compared region specialists
trained *outside* the frozen run against E0. That is the purity gap the routing
result had. These runs close it for the verifier claim too: the built system's
components were trained inside the frozen evidence, from the improver's own
history, and the comparison against the frozen base evaluator E0 is:

| | E0 | pooled at 24 | built at 24 | built minus E0 | pooled minus E0 |
| --- | --- | --- | --- | --- | --- |
| rep 1 | 320 | 328 | 357 | **+37**, 11w/1l, interval **+20 to +56** | +8, interval -2 to +18 |
| rep 2 | 326 | 332 | 358 | **+32**, 9w/1l, interval **+18 to +44** | +6, interval -11 to +22 |

Pooling the same labels barely moves E0 and both of those intervals cross zero.
The evaluator improvement is a product of construction, not of label volume, and
every component behind it is audited.

## Honest reading of E4

Replication two is **not monotone**: built dips from 362.7 at sixteen banks to
358.0 at twenty-four. The five-fold rotation on opened panels agreed, with four
of five folds monotone. Replication one's clean curve was the luckier draw and
should not be quoted alone.

So growth in this improver is real and replicated in aggregate, and it is **not
strictly monotone in history size**. More history helps on average; it is not
guaranteed to help at every step.

## Audits

Replication one: **passed**. 1,728 tasks regenerated from seeds, all pools and
both candidate orders recomputed, 161,452 candidate labels rechecked, the cached
feature matrices verified, and the whole construction curve rebuilt. Every curve
point reproduced exactly. Zero failures.

Replication two: **passed**. 1,728 tasks regenerated, 161,732 candidate labels
rechecked, feature matrices verified, every curve point reproduced exactly
(309.7, 334.2, 362.7, 358.0). Zero failures.

**Both replications pass E1, E2 and E3 with passing independent audits**, which
is the predeclared reporting rule. The claim is therefore unconditional, subject
to the limits below.

The auditor imports none of the improver's procedure. Partition, specialist
training, router fitting and deployment are written out again in the auditor so
a bug in the runner cannot be reproduced by shared code. It also checks the
cached feature rows, which the construction improver trains on directly and the
routing experiment never had to verify.

## Supporting evidence on opened panels

A five-fold rotation of the held-out panel passed both development gates in
**5 of 5 folds**: D1 +55, +45, +47, +54, +24 and D2 +89, +80, +71, +73, +54. The
built-minus-pooled gap widened monotonically in every fold, mean **9.8, 18.0,
24.8, 37.4, 45.0** at 4, 8, 16, 32 and 48 history banks, with mean construction
growth **73.4** against pooled **37.0**.
See `analysis/construction-improver-rotation-20260921.json`.

## What is still not claimed

- **Recursive growth.** Tested and failed; see `RECURSIVE-GROWTH-2026-09-21.md`.
  Parents transmitting a partition scheme produced children scoring 366, 364,
  366 and 362 for early, late, default and scrambled. The cause was screened
  afterwards: default regret over the scheme catalog is +1, +11, +2 and +13 at
  child history sizes 3, 6, 12 and 24, all below the +20 bar.
- **The partition rule.** Bin edges on first-correct rank are researcher
  written. The improver computes the partition and trains every model, but did
  not invent the rule. This is the remaining purity gap.
- **Generality.** One synthetic benchmark, one notion of complexity. Nine action
  spaces failed before one succeeded, so the result depends on environment
  structure and not only on the learner.

## Limits

- The complexity bin derives from the base ranker's order, so it is latent but
  not independent of that ranker.
- Strided windows over one history pool are not independent samples.
- The pooled baseline shares the improver's feature representation; a different
  representation could change both arms.

## Withdrawal, 2026-09-21

Two review findings were checked on both frozen replications with
`construction_oof_audit.py`, which reuses the audited caches and generates
nothing.

**Out-of-fold routing.** `fit_router` was fitted on specialist predictions for
the specialists' own training rows. Refitting it on three-fold out-of-fold views
lowers the built system by **14.0** (interval +1.0 to +27.0) at 24 banks in
replication one and by -1.0 (interval -15.0 to +13.0) in replication two. The
leakage was real and it inflated one replication.

**Capacity-matched pooling.** The built system holds up to four models of 15
leaves plus a router. One pooled model with 60 leaves, on exactly the same
history, beats the out-of-fold built system at every history size in both
replications.

| `built_oof` at 24 banks against | rep 1 | rep 2 |
| --- | --- | --- |
| `pooled`, 15 leaves | E1 +15.0, interval -3.0 to +37.0; E3 +6.7, interval -12.8 to +29.8 | E1 +27.0, interval +9.0 to +45.0; E3 +13.5, interval -2.3 to +30.0 |
| **`pooled_capacity`, 60 leaves** | **E1 -50.0, interval -68.0 to -33.0**; E3 -22.0, interval -45.5 to 0.0 | **E1 -36.0, interval -51.0 to -22.0**; E3 -15.7, interval -32.3 to +0.3 |
| `pooled_featured`, 15 leaves plus router statistics | E1 +19.0, interval +2.0 to +40.0; E3 +5.8, interval -10.7 to +26.2 | E1 +33.0, interval +14.0 to +52.0; E3 +18.3, interval +2.3 to +34.7 |
| in-sample router minus OOF router | **+14.0, interval +1.0 to +27.0** | -1.0, interval -15.0 to +13.0 |

Curves, expected total per history size:

| history | rep 1 built OOF | rep 1 pooled 60 | rep 2 built OOF | rep 2 pooled 60 |
| --- | --- | --- | --- | --- |
| 4 | 316.2 | 344.2 | 316.2 | 336.5 |
| 8 | 322.5 | 366.8 | 330.8 | 363.2 |
| 16 | 337.2 | 381.0 | 353.0 | 385.2 |
| 24 | 343.0 | 393.0 | 359.0 | 395.0 |

**What this changes.**

- E1 against the protocol's own baseline drops to **+15.0 (interval crossing
  zero)** and +27.0 after out-of-fold routing. Against a capacity-matched
  baseline it is **-50.0 and -36.0**. E1 is withdrawn.
- E3 crosses zero against every baseline in at least one replication and is
  negative against the capacity-matched one in both. E3 is withdrawn.
- E2 survives: the built system improves with history (316.2 to 343.0 and 316.2
  to 359.0). So does the pooled model (344.2 to 393.0 and 336.5 to 395.0). E2
  alone establishes that more verified data helps, which is not an improver
  claim.
- Feature augmentation does not explain the gap: `pooled_featured` scores 324.0
  and 326.0, below plain pooling. The router's task statistics are not the
  source of value.

**What survives from these runs.** Verifier growth is strengthened, not
weakened: the capacity-matched pooled model beats the frozen base evaluator E0
by **+73 and +69** at 24 banks, and it is now the strongest evaluator built
inside a frozen run. The reproducibility machinery, the protocol hashing and the
independent audits performed exactly as designed; they reproduced a flawed
specification faithfully, which is the difference between a reproduction audit
and an information-flow audit.

**Why the frozen audits passed.** The auditor re-derived the runner's procedure
from the same specification, including in-sample router fitting and a 15-leaf
pooled baseline. It could not detect that the specification itself was the
problem. An information-flow audit and an adversarial-baseline check are
distinct from reproduction and must be run separately.

**Matched-capacity check, resolved.** `construction_capacity_audit.py` gives the
specialists and the pooled member 60 leaves each, fits the router out of fold,
and compares against single pooled models at 60 and 120 leaves on the same
history.

| history | rep 1 built-60 | rep 1 pooled-60 | rep 1 pooled-120 | rep 2 built-60 | rep 2 pooled-60 | rep 2 pooled-120 |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | 335.5 | 344.2 | 351.5 | 331.2 | 336.5 | 355.3 |
| 8 | 351.7 | 366.8 | 377.5 | 354.8 | 363.2 | 383.5 |
| 16 | 375.0 | 381.0 | 400.7 | 392.0 | 385.2 | 405.3 |
| 24 | 399.0 | 393.0 | 404.0 | 398.0 | 395.0 | 410.0 |

| built-60 at 24 banks | rep 1 | rep 2 |
| --- | --- | --- |
| E1 vs pooled-60 | +6.0, interval -6.0 to +18.0 | +3.0, interval -10.0 to +17.0 |
| E3 vs pooled-60 | **+14.7, interval +0.3 to +30.3** | +8.3, interval -5.8 to +21.8 |
| E1 vs pooled-120 | -5.0, interval -14.0 to +3.0 | -12.0, interval -25.0 to +1.0 |
| E3 vs pooled-120 | +11.0, interval +1.7 to +21.2 | +12.2, interval -5.7 to +29.5 |

At matched per-component capacity, partitioning trails while history is small,
because it splits scarce data across bins, and is level with pooled-60 by 24
banks: E1 +6.0 and +3.0, both intervals crossing zero. E3 against pooled-60 is
weakly positive, clearing zero by 0.3 in one replication and crossing it in the
other. That is a hint that a partitioned system extracts more from growing
history than a single model of the same per-component size; it is not a result
under the two-replication reporting rule. Pooled-120 beats built-60 at every
history size in both replications and is not saturated.

The withdrawal stands: nothing built in this programme beats one larger model on
the same labels. What this check adds is that the residual at matched capacity
is small and inconsistent rather than zero. Resolving it would need a frozen
study with pooled models at several sizes in the default set and substantially
more than twelve banks per replication. That is a candidate next experiment. It
is not a claim.

**Combined capacity-and-feature-matched baseline, resolved.**
`combined_capacity_feature_baseline.py` gives the pooled model both matched
leaves and the router's five task statistics appended to every candidate row,
on the same strided windows.

| history | rep 1 built-60 | pooled-60 | pooled-60+f | pooled-120 | pooled-120+f | rep 2 built-60 | pooled-60 | pooled-60+f | pooled-120 | pooled-120+f |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 335.5 | 344.2 | 343.3 | 351.5 | 353.0 | 331.2 | 336.5 | 338.0 | 355.3 | 351.2 |
| 8 | 351.7 | 366.8 | 364.5 | 377.5 | 379.3 | 354.8 | 363.2 | 362.3 | 383.5 | 382.3 |
| 16 | 375.0 | 381.0 | 384.3 | 400.7 | 401.3 | 392.0 | 385.2 | 382.5 | 405.3 | 407.2 |
| 24 | 399.0 | 393.0 | 390.0 | 404.0 | 409.0 | 398.0 | 395.0 | 395.0 | 410.0 | 409.0 |

| at 24 banks | rep 1 | rep 2 |
| --- | --- | --- |
| pooled-60+f minus pooled-60 | -3.0, interval -13.0 to +6.0 | +0.0, interval -10.0 to +10.0 |
| pooled-120+f minus pooled-120 | +5.0, interval -3.0 to +13.0 | -1.0, interval -11.0 to +10.0 |
| built-60 minus pooled-60+f | +9.0, interval -3.0 to +21.0 | +3.0, interval -13.0 to +19.0 |
| built-60 minus pooled-120+f | -10.0, interval -20.0 to 0.0 | -11.0, interval -24.0 to +4.0 |

The task statistics the router sees add nothing to a pooled model at either
capacity. The gap the built system once showed over "pooled" was capacity and
nothing else. Stage 1 of the third review's staging is closed.