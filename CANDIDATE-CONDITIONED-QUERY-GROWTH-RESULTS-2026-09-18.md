# Candidate-conditioned query evaluation and improver transfer

Status: **fresh evaluator component gate passed; incremental child-improver growth gate failed.** The evaluator result is for a synthetic six-mechanism string/program benchmark, E0's frozen candidate pools and ranker, one frozen probe per task, and eight output calls per 48-task bank. Full source/target candidate replay and child-decision reconstruction passed.

## Why this edit

The previous evaluator learned to rank candidates, but its inherited query controller selected only 19 of 77 available first-query fixes on a 576-task panel. Query value depends on what the reranker placed first and which alternative predicted answers a probe could distinguish. A new 26-feature value model retains the prior 12 public features and adds E0 top-choice old rank/score, predicted answer-group entropy and sizes at the frozen probe, cross-probe agreement, and agreement of the old, E0, E1 and 7-leaf rankers. A public-mechanism interaction ridge model predicts the verified one-call-minus-zero-call gain for the **E0** ranker. It then buys the eight highest predicted gains in each bank. The oracle's target outputs and final correctness labels are never input features.

On two opened, audited source panels (1,152 tasks, 24 banks), leave-one-bank-out correct choices at eight calls per bank were 724 for conditioned interactions, 714 for the same features without interactions, 713 for the old features refit on the same data, and 708 for the frozen incumbent allocator. The interaction model's source gain-forecast MSE was 0.1221 versus incumbent 0.1334. This screen selected one rule before new seeds 902534-902545 were generated. Protocol: `EXPERIMENT-candidate-conditioned-query-transfer.md`; development results: `analysis/candidate-conditioned-query-development-20260918.json`.

## Third untouched panel: evaluator result

All policies used identical E0 candidate order, old-frozen top-20 entropy probe and **96 total output calls** across 576 new tasks. Only call locations changed.

| Query allocator | Correct / 576 | Selected fixes | Gain-forecast MSE |
| --- | ---: | ---: | ---: |
| E0, no output calls | 349 | 0 | — |
| Frozen incumbent | 374 | 25 | 0.12552 |
| Old 12 features, matched 1,152 source tasks | 373 | 24 | 0.12035 |
| 26 features, no mechanism interaction, matched source | 380 | 31 | 0.11474 |
| Initial conditioned interaction, 576 source tasks | 383 | 34 | 0.11298 |
| **Later conditioned interaction, 1,152 source tasks** | **387** | **38** | **0.11144** |
| Scrambled additional feedback | 381 | 32 | 0.11500 |
| Duplicated initial feedback | 384 | 35 | 0.11316 |

Later minus incumbent was **+13** correct choices, positive in ten banks, zero losing banks, with exact paired bank-bootstrap interval **[+9,+17]**. The gain forecast MSE also fell; the frozen evaluator promotion gate passed. Later exceeded the matched-data old-feature control by +14, interval [+9,+19], and the same-feature no-interaction control by +7, interval [+2,+12]. Thus the gain is associated with the candidate-conditioned features and mechanism interactions, not just additional source rows or calls. Later exceeded scrambled feedback by +6, interval [+3,+9], although this is one synthetic transfer panel.

The new allocator recovered 38 of 78 query fixes available to an unavailable hindsight eight-call allocator, versus 25 for incumbent; selected-gain regret fell from 53 to 40. The fresh full candidate pool contained a correct candidate for 496/576 tasks; the old top 20 contained one for 449. These are separate search/shortlist limits, not query gains.

The observed later-minus-incumbent family changes were +10 self-edit, +6 mutation, 0 AST and novel-operator, -2 transformation and -1 stack. Later placed 20 calls on self-edit and 43 on mutation versus incumbent's 2 and 23. This mechanism breakdown was computed after scoring and is explanatory, not a separate validated rule.

## Incremental parent-to-child outcome

The earlier parent inherited 576 opened source query effects; the later inherited all 1,152. The same frozen learning rule produced both children from the same E0 base. The later child passed the six-bank admission comparison: 189/288 versus initial 187, incumbent 183 and old-feature matched-data 180. On the separate six-bank protected transfer, later scored **198/288 versus initial 196**. Only two banks improved and the paired interval was **[0,+4]**. The declared child-growth rule required at least +4, four positive banks and a positive lower endpoint. It failed. The later child exceeded scrambled and duplicate controls on transfer (195 and 197), but that does not repair the failed primary gate. This is a better fixed evaluator, **not yet a self-improving improver**.

## Costs, audit and next decision

The target preparation generated 99,104 base candidates and 34,590 added AST candidates, rescored 11,280 top-20 entries, predicted 1,069,552 candidate/probe outputs, and took 297.2 seconds of wall time (1,426.7 summed parallel candidate-generation seconds). The research oracle checked 133,694 final candidate labels; each budgeted child used 96 logical exact-output calls. The later value model additionally acquired 576 historical task-level query-effect records relative to initial. The underlying E0 candidate reranker had itself been trained on 11,282 earlier verified candidate labels. Historical source acquisition and training are not free.

The candidate-conditioned features use E1 and 7-leaf top-choice agreement. Deploying them adds two model prediction passes on the same 11,280 top-20 feature rows beyond the E0 ranker. The offline harness computed all four rankers for every policy, so wall-clock results do **not** prove total-compute superiority over the cheaper incumbent. The fixed-output-call superiority is supported; a cost-matched ablation of those agreement features remains necessary before calling this the optimal seed.

The independent audit retrained four source candidate models, rebuilt 864 earlier candidate-label training tasks and 16,948 labels, regenerated all 576 target tasks/pools, checked 11,280 rerankings, 1,069,552 output predictions, 12 fixed allocations and 133,694 final candidate labels. A separate reconstruction refit all seven value policies and rechecked 4,032 target child decisions. Both passed. Machine results: `runs/candidate-conditioned-query-transfer-20260918/conditioned_results.json` and `runs/candidate-conditioned-query-transfer-20260918/audit.json`.

Retain the E0 reranker and **promote the candidate-conditioned interaction query evaluator for this tested synthetic contract at a fixed output-call budget**. Keep its later-feedback child-growth claim unpromoted. Next test the minimum-cost feature set and a conditional post-query or search edit in a same-base parent/child study on another untouched bank, charging source labels and all model inference. A positive feedback loop requires later parents to produce better children repeatedly, not a single better fixed evaluator.
