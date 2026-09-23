# Region-acquisition improver transfer, 2026-09-20

Protocol: `EXPERIMENT-region-acquisition-improver-transfer.md`, predeclared
before any fresh bank for this study existed.
Run: `runs/region-acquisition-improver-transfer-20260920/`.

## Outcome in one line

The evaluator component gate passed decisively on fresh banks (+49/576, twelve
of twelve banks, interval +37 to +62). Both improver-growth gates failed, and
the run explains why in a way the previous forty failures did not: after the
later parent's purchase, an unavailable oracle had only **+5 and +1** of
selection headroom left, while **+69 and +79** of ranking headroom remained.

## What was tested

One acquisition unit buys every verified top-100 candidate label for one public
region and trains that region's specialist reranker. Parents differ only in
inherited verified repayment records and share the same frozen base, the same
six specialists, the same budget of three units and the same selection rule.

| parent | inherited | selection |
| --- | --- | --- |
| `initial` | 1 opened panel | ast, transform, **mutation** |
| `later` | 3 opened panels | ast, transform, **novel_operator** |
| `duplicate` | initial panel x3 | ast, transform, **mutation** |
| `scrambled` | 3 panels, labels permuted | novel_operator, self_edit, stack |
| `empty` | none; largest mean pool | ast, novel_operator, stack |

## Results

Correct zero-query top choices per 576 tasks.

| policy | bank B | bank C |
| --- | --- | --- |
| E0, no specialist | 336 | 345 |
| `scrambled` | 356 | 367 |
| `empty` / `largest_pool` | 369 | 388 / 383 |
| `initial` = `duplicate` | 379 | 383 |
| **`later`** | **385** | **388** |
| oracle best 3, unavailable | 390 | 389 |
| all six units, twice the budget | 399 | 405 |

### G1, evaluator component: **passed**

`later`'s installed system scored 385 against E0's 336. Gain +49, twelve of
twelve banks positive, no losing bank, interval **+37 to +62**. This replicates
the opened-panel finding on banks generated after the protocol was frozen.

### G2, improver growth: **failed**

`later` minus `initial` was **+6** with six winning and three losing banks and
interval **-3 to +15**. The predeclared gate required the interval to exclude
zero. `duplicate` scored identically to `initial` on both banks, so the +6 is
attributable to the information in the extra history rather than to record
volume, but it is not separable from bank noise.

### G3, recursive child growth: **failed**

After a common admission observation, C(`later`) minus C(`initial`) was **+5**,
five winning and two losing banks, interval **-1 to +12**. Same verdict.

## Why the improver was directionally right and still failed

The later parent's reasoning was correct. Mutation, the region it declined,
realized **-1** on bank B and **+2** on bank C, matching the three-panel
estimate of 0.3 rather than the single-panel estimate of +14. The later parent
beat the initial parent on both fresh banks and was never behind in aggregate.

The gate failed because the decision could not be worth enough. Value is
concentrated in the two regions every informed parent already buys: on bank B,
ast realized +23 and transform +21 of the +49 total, leaving the third pick
worth about +5. A marginal decision worth +5 cannot clear a twelve-bank interval
whose width is about 18.

## The measurement that matters

Decomposed on the same fresh banks, same tasks, same accounting:

| quantity | bank B | bank C |
| --- | --- | --- |
| construction value: all six specialists over E0 | **+63** | **+60** |
| selection ceiling at budget 3: oracle over E0 | +54 | +44 |
| captured by `later` | +49 | +43 |
| **selection headroom left after `later`** | **+5** | **+1** |
| **ranking headroom left after all six** | **+69** | **+79** |

Head reachability was 468 and 484 of 576; all six specialists reached 399 and
405.

This repeats, at a ten-times-larger scale, the pathology found in
`analysis/edit-catalog-headroom-20260918.json`, where oracle selection among
whole-bank policies was worth 5 and 8. Enlarging the action space from whole-bank
policies to region purchases multiplied the *total* available value by roughly
ten, but left the *marginal* decision worth the same +1 to +5, because the
leading options are stable and any competent policy takes them.

The conclusion is not that this improver is unintelligent. It is that
**selection is the wrong verb**. Every replicated gain in this project has come
from *constructing* a new evaluator component: +35 for the first E0 reranker,
+21 and +42 for the two AST specialists, +49 here. Every failure has come from
*choosing* among components already built. The next improver test must put
construction inside the improver's action space.

## Costs

135,728 candidate labels checked across 1,440 fresh tasks; 135,728 candidates
rescored at deployment; 528 s bank preparation. Each parent bought three
acquisition units; `all_six` bought six and is not cost-matched.

## Audit

`runs/region-acquisition-improver-transfer-20260920/audit.json`. The auditor
regenerates all three banks from seeds, rebuilds every candidate pool, recomputes
both candidate orders, rechecks every final label, and reconstructs each parent
and child selection from the inherited records alone, then recomputes all totals
and gates without importing the runner's scoring.

## Limits

- One synthetic string/program benchmark.
- Specialists share E0's candidate pool and order, so this measures ranking only.
- Budget 3 was chosen on opened development data so the two parents would select
  differently. That makes G2 a fair test of whether extra history helps; it is
  not an unbiased estimate of how often a budget of 3 matters in deployment.
- `later` beat `initial` on both fresh banks in the predicted direction. That is
  suggestive and it is not a growth claim: the declared gate governs.
