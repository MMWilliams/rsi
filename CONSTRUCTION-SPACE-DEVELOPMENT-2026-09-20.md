# Construction action space, opened development screens, 2026-09-20

Development evidence on already-opened panels. No policy is frozen here.
Sources: `analysis/construction-space-development-20260920.json`,
`analysis/region-depth-development-20260920.json`.

## Why

`REGION-ACQUISITION-IMPROVER-RESULTS-2026-09-20.md` showed that *selecting*
among prebuilt specialists left only +5 and +1 of oracle headroom on fresh banks,
while +69 and +79 of ranking headroom survived every selection. These screens
measure the alternative verb: **constructing** the component, under one matched
verified-label budget.

## Screen 1: global construction at a matched budget

Twelve cost-matched constructions at L = 40,000 verified candidate labels from
two source panels, each scored on three opened target panels against frozen E0.
A construction chooses which source tasks to label (composition) and how many
candidates per task (depth).

Gain over E0, summed over the three panels:

| construction | labels | tasks labelled | total |
| --- | --- | --- | --- |
| e0_wrong@25 | 28,487 | 1,152 | **+64** |
| top_regions@25 | 28,487 | 1,152 | +63 |
| low_margin@25 | 28,487 | 1,152 | +60 |
| uniform@25 | 28,487 | 1,152 | +53 |
| top_regions@50 | 39,974 | 811 | +15 |
| uniform@50 | 39,996 | 819 | -26 |
| uniform@100 | 39,966 | 424 | -48 |
| low_margin@50 | 39,986 | 808 | -59 |
| top_regions@100 | 39,952 | 400 | -129 |
| low_margin@100 | 39,930 | 406 | -145 |
| e0_wrong@100 | 40,000 | 406 | **-217** |

Cost-matched spread is **281**, against a twelve-bank interval half-width of
about 9. The power precondition P2 in
`TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md` is satisfied by a wide margin.

Two cautions apply to this table. At depth 25 the budget does not bind: all
1,152 source tasks fit, so those four arms train on the same rows in a different
order and their +53 to +64 spread is a training-noise floor, not a composition
effect. And each deep arm is also *tested* over a wider shortlist, so depth is
confounded with decision difficulty. Screen 2 resolves that.

The same twelve models scored across all three test widths
(`analysis/global-depth-completion-20260920.json`):

| global uniform | test 25 | test 50 | test 100 |
| --- | --- | --- | --- |
| **train 25** | **+53** | +45 | +45 |
| **train 50** | -22 | -26 | -14 |
| **train 100** | -55 | -49 | -48 |

Depth hurts the global model at every test width, so the collapse is not a
decision-difficulty effect.

## Screen 2: region routing crossed with depth

Six region specialists trained at depth 25, 50 and 100, each scored at test
width 25, 50 and 100. Gain over E0, summed over the same three panels:

| | test 25 | test 50 | test 100 |
| --- | --- | --- | --- |
| **train 25** | +177 | +207 | +205 |
| **train 50** | +194 | +219 | +226 |
| **train 100** | +179 | +218 | **+233** |

Testing wider is better or flat at every train depth. The depth-100 collapse in
screen 1 was therefore **a worse model, not a harder decision**: under the 40,000
budget cap, depth 100 labelled only 424 of 1,152 tasks and lost task breadth.

## Corrected reading

The first reading of screen 1, that depth dominates composition and shallow
labelling wins, was an artifact of the budget cap acting on a single global
model. The regional grid reverses it: for region specialists, deeper training
helps.

The comparison that matters is cost-matched, and the two screens land on the
same cell exactly: global uniform@25 labels 1,152 source tasks for 28,487
labels, and region@25 labels the same 1,152 tasks, 192 per region, for 28,800.
**Identical label spend and identical task coverage.**

| construction | training labels | source tasks | test 25 | test 100 |
| --- | --- | --- | --- | --- |
| global uniform@25 | 28,487 | 1,152 | +53 | +45 |
| **region@25** | 28,800 | 1,152 | **+177** | **+205** |
| region@100, uncapped | ~130,000 | 1,152 | +179 | +233 |

**Splitting one model into six region models is worth +124 at test width 25 and
+160 at test width 100, at the same label cost and the same source tasks.** The
gain is specialization, not data volume. Depth adds about +28 more for roughly
four times the labels. Test width is worth up to +28 and costs no labels at all,
only inference.

## What this implies for the improver

The construction space clears P2 and is the right place to test improver growth.
But the shape is familiar and worth naming before the next frozen run: one
dominant choice, region routing, worth +150; then depth and width worth +28
each; then composition inside training noise. This is the same structure that
made the previous four improver gates unwinnable, one level up.

The open question is no longer whether the action space is big enough. It is
whether the **optimal action varies across banks**. If every bank prefers the
same construction, a parent with one observation matches a parent with twenty,
and improver growth stays unmeasurable no matter how large the total value is.
`action_space_stationarity.py` measures exactly that from the audited per-bank
rows, and its answer decides whether Phase 1 of the technical design is worth
running or whether the environment itself has to change.

## Limits

- Opened panels; all numbers are development evidence.
- Widths are nested prefixes of one cached top-100 candidate order, so these
  screens vary labelling and decision depth, not candidate coverage.
- Region arms in screen 2 were not budget-capped; their label spend is reported
  per depth and differs from the global arms except at depth 25.
- `e0_wrong` charges one verified label per screened task, and
  `reachable_e0_wrong` charges full head labels, so the latter is a
  cost-unmatched reference and never a competing arm.
