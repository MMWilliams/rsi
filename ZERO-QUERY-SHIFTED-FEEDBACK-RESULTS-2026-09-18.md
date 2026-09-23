# Incremental evaluator feedback: shifted AST first-choice test

## Decision

The two frozen evaluator gates passed on 24 fresh shifted AST banks (192 tasks). The later checkpoint made 74 correct first choices before any output call, versus 60 for its earlier parent and 23 for E0. Additional verified candidate feedback corrected 14 of the parent's first-choice errors and introduced none on this bank. This establishes **scoped incremental evaluator growth** on the changed AST mechanism. It does not establish an improving improver, general transfer, or compounding search coverage.

The independent reconstruction status and counts are in `runs/zero-query-shifted-feedback-transfer-20260918/audit.json`. The frozen protocol is `EXPERIMENT-zero-query-shifted-feedback-transfer.md`; full bank outcomes and paired differences are in the run's `results.json`.

## Frozen design and results

All policies saw identical V67/V73 widened candidate pools. The zero-call result is final correctness of the ranker's first candidate. The budgeted result applies the same four exact output calls per bank. The A model used 9,566 verified candidate labels from 96 earlier shifted tasks. AB used those plus 18,906 labels from 192 later shifted tasks, 28,472 total. AB-scrambled permuted the later labels within each task. Model files and hashes were frozen before generating the target bank.

| Evaluator | Zero calls | One call on every task | Fixed 96-call budget |
|---|---:|---:|---:|
| E0 | 23/192 | 54/192 | 37/192 |
| Familiar top-50 | 12/192 | 52/192 | 29/192 |
| A, shifted top-100 | 60/192 | 75/192 | 70/192 |
| AB, later shifted top-100 | **74/192** | **79/192** | **77/192** |
| AB with later feedback scrambled | 50/192 | 71/192 | 61/192 |

The A-versus-E0 zero-call gain was **+37**, with 19 positive and zero losing banks; its paired bank interval was **+26 to +48**. The later AB checkpoint gained **+14** over A, with nine positive and zero losing banks, interval **+6 to +23**. AB beat its scrambled-feedback control by **+24**, with 13 positive and zero losing banks, interval **+14 to +35**. All declared component and incremental evaluator gates passed. At the fixed 96-call schedule, AB exceeded A by seven, interval +2 to +13. At the task level, the later checkpoint corrected 14 A errors and caused zero new first-choice errors on these 192 tasks.

The full candidate pool contained a correct program for **105/192** tasks, and the old top 100 contained one for **90/192**. The AB zero-call choice solved 74 of those 90 top-100-reachable tasks. Its fixed-budget result added only three over its own zero-call result, so candidate ranking is currently the dominant observed gain on this changed mechanism. The shared pool generation charged 26,762 base candidates and 68,204 added AST candidates. Preparing public records required 759,728 predicted probe-output cells; each shifted top-100 model scored 19,092 candidates. Equal output-call budgets do not imply equal training or inference costs.

## What this changes in the research program

The strongest measured evaluator edit is now **feedback-trained candidate ranking before the sensor call** on shifted AST tasks. The previous mixed applicability router learned from 96 added effect records but did not improve its fixed-threshold choices, and routing between E0 and the post-query specialist had only seven tasks of oracle headroom at the fixed call budget. The new ranker changes the action set and moves the zero-call operating point substantially.

Do not apply AB globally: an opened familiar AST screen scored only 2/96 zero-call choices for AB against E0's 13. The next protected integration test must use public task evidence to decide when this ranker applies, with familiar-task safety and charged candidate-scoring cost. A distinct **improver** test should give earlier and later edit controllers identical base evaluator, proposal catalog, feedback and child budgets, then compare their frozen child evaluators on a second untouched bank. A fixed later ranker by itself does not show that the system became better at improving itself.
