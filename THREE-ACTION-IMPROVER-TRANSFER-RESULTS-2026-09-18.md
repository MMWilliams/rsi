# Three-action evaluator controller: fresh transfer result

## Decision

The prospectively frozen three-action controller **failed both gates** on 24 untouched mixed AST banks (192 tasks). Its later checkpoint selected **42** correct first programs with zero external output calls, versus **43** for its earlier parent, **45** for balanced duplicate history, **39** for scrambled new outcomes, **42** for the prior two-action route, **36** for always shifted AB, **38** for always pooled and **27** for E0. Later-minus-early was **-1**, paired bank interval **-4 to +2**. Later-minus-duplicate was **-3**, interval **-6 to 0**. The fixed-action integration comparison against AB was +6, interval **0 to +12**, short of the declared +8 and strictly positive interval requirements. No child-improver growth or general seed promotion is supported.

The independent audit passed. It rebuilt all 192 tasks, 480 source action rows, 745,824 predicted output cells, 93,228 final candidate labels, 18,948 candidate scores for each of A, AB and pooled, and 2,304 controller action scores. The frozen protocol is `EXPERIMENT-three-action-improver-transfer.md`; complete paired bank results and audit are in `runs/three-action-improver-transfer-20260918/`.

## Same-bank comparison

| First-choice policy | All 192 | Familiar 96 | Shifted 96 |
|---|---:|---:|---:|
| E0 | 27 | 15 | 12 |
| Shifted AB | 36 | 0 | **36** |
| Pooled | 38 | **17** | 21 |
| Prior two-action route | 42 | 10 | 32 |
| Earlier three-action controller | **43** | 10 | 33 |
| Later three-action controller | 42 | 10 | 32 |
| Scrambled added outcomes | 39 | 6 | 33 |
| Balanced duplicate history | **45** | 12 | 33 |

The later controller had a positive point difference against AB (+6), but it improved only nine banks and lost three; the paired interval included zero. It tied the prior two-action route with more actions and training. The duplicate-history controller outperformed the later controller on three banks and lost none. Feedback that merely adds rows or actions did not produce a stronger improver on this target.

## Bottleneck decomposition

The full candidate pool contained a correct program for **102/192** tasks and the old top 100 for **92**. A hindsight choice among the three frozen first-choice actions could solve **56**, leaving **36 top-100-reachable tasks** missed by all three action heads. The later controller solved 42 of the 56 action-reachable tasks. On familiar AST alone, 46/96 tasks had a correct top-100 candidate but the three-action hindsight ceiling was only 20 and the later controller solved 10. On shifted AST, top-100 reachability was 46, the three-action ceiling 36, and later selected 32. Thus candidate-level ranking on familiar AST is the larger measured opportunity than routing these three fixed first choices.

The shared generator produced 18,948 top-100 candidate scores per ranker and 745,824 predicted probe-output cells, although the primary outcome bought zero external output calls. Training used 288 earlier task outcome rows and 192 additional verified mixed rows; controls kept nominal added-row counts. Equal output-call counts do not establish equal total training or inference cost.

## Next seed test

Keep the validated shifted AB evaluator as a scoped specialist. Keep E0 as the conservative general operating point until a routed or joint candidate evaluator passes a protected mixed-bank gate. Test a **familiar-AST-specific candidate ranker** and its incremental feedback checkpoints, then revisit multi-action integration with materially stronger action choices. A controller cannot recover tasks whose correct program none of its actions selects.
