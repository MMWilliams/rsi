# Region-specialist repayment, opened development screen, 2026-09-20

Development evidence on already-opened panels. No policy is frozen here and no
growth claim is made from this file.

## Why this screen exists

Roughly forty improver tests in this project have failed their growth gates. The
`analysis/edit-catalog-headroom-20260918.json` audit explains most of that
record: on the two latest 576-task runs, an **unavailable oracle choosing among
the tested whole-bank policies** would have gained only **5 and 8** correct
tasks. Paired bank-level noise on those same runs was of the same magnitude.

Every improver gate so far asked a learned policy to beat its controls inside
that 5-to-8 band. A perfect improver would have failed most of them. The failures
are therefore only weak evidence about improver intelligence; they are strong
evidence that the **action space was too coarse to measure it**.

By contrast, the same audit put individual output-call placement headroom at
**50 and 48** on those runs, and the bottleneck dissection
(`SEED-IMPROVER-BOTTLENECK-DISSECTION-2026-09-18.md`) put the
reachable-but-unselected gap at **143** per 576 tasks. The action space, not the
learner, was the binding constraint.

## What was measured

One **acquisition unit** buys every verified top-100 candidate label for one
public region across two source panels
(`candidate-reranker-transfer-20260918`, `candidate-reranker-replication-20260918`,
192 tasks per region) and trains that region's specialist reranker. Regions are
the six public task families; family is exactly recoverable from the public
Unicode block, so no hidden metadata is used.

Each specialist was then scored on three separate opened 576-task panels against
the frozen E0 reranker, at **zero output calls, on identical candidate pools and
identical candidate order**. This isolates ranking from coverage.

## Result

Repayment over E0, in correct zero-query top choices per 576-task panel:

| region | c-query-cost | combined-ranker | c-conditioned | mean |
| --- | --- | --- | --- | --- |
| ast_transition | +32 | +32 | +19 | 27.7 |
| transform_transition | +28 | +18 | +27 | 24.3 |
| novel_operator_transition | +10 | +14 | +17 | 13.7 |
| stack_transition | +8 | +5 | +9 | 7.3 |
| self_edit_transition | +4 | +5 | +4 | 4.3 |
| mutation_transition | +14 | -6 | -7 | 0.3 |

Installing all six specialists scored **423, 412 and 418** against E0's
**327, 344 and 349**, with head reachability 490, 487 and 483. Per-region paired
bank intervals are in
`analysis/region-specialist-repayment-development-20260920.json`; ast and
transform are positive in 9 to 12 of 12 banks on every panel, while mutation
ranges from 8 wins and 2 losses on one panel to 3 wins and 5 losses on another.

## Why this is the right action space for an improver test

Two properties matter, and both hold here.

1. **Headroom.** The spread between the best and worst three-region purchase is
   roughly 50 correct tasks per 576, an order of magnitude above the 5-to-8 band
   that every previous improver gate lived inside.
2. **A genuine learning problem.** Repayment is heterogeneous *and* partly
   unstable. Mutation is the informative case: a single panel of history ranks it
   the third-best buy, three panels rank it last. An improver with more verified
   history should decline it. That is a mechanism by which extra history can
   produce a better purchase, rather than a hope that a bigger table helps.

## Limits

- Opened panels; every number above is development evidence.
- Specialists share E0's candidate pool and order, so this measures ranking only.
  It does not address candidate coverage, where a separate 143-task gap sits.
- Repayment is measured at zero output calls. A ranker edit is known from
  `COMBINED-RANKER-QUERY-RESULTS-2026-09-18.md` to reduce the value of later
  sensing, so these gains should not be added to sensor gains.
- The frozen test of whether an improver can *use* this structure is
  `EXPERIMENT-region-acquisition-improver-transfer.md`, predeclared before any
  fresh bank for it was generated.
