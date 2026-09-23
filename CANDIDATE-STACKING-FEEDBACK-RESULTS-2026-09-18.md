# Stacked specialist evaluator: fresh feedback test

The candidate-level stack improved the fresh mixed-bank score modestly, but **neither evaluator-growth nor integration promotion passed the frozen gates**. Added verified candidate feedback changed the later checkpoint from 66 to 68 correct choices, a +2 difference with a paired bank interval of -2 to +6. The later stack scored 68 versus 64 for the frozen dual-specialist confidence route, with interval -1 to +10 and only four positive banks. This does not establish a retained evaluator improvement from the additional feedback, much less a growing improver.

## Setup and audit

The [protocol](EXPERIMENT-candidate-stacking-feedback-transfer.md) froze 24 new eight-task mixed familiar/shifted AST banks, common candidate pools and old-ranker order. A stacked candidate ranker used structural/ranking features and both specialists' candidate probabilities. The early model trained on 38,058 verified top-100 candidate labels from 384 opened tasks; later added 19,092 labels from 192 more tasks. Scrambled-within-task and repeated-history controls used the same model class. Target choices and costs were frozen before hidden-example labels were scored. No task family or target oracle result entered the choices.

The [audit](runs/candidate-stacking-feedback-transfer-20260918/audit.json) passed: 192 tasks, 791,056 candidate-output prediction cells, 266,392 frozen model prediction cells, 98,882 exact candidate labels and 96 fixed-width allocations were rebuilt. This verifies the target replay and frozen model-file use. It does not independently rederive every source model weight or show transfer outside the synthetic AST mix.

## Fresh target results

| Zero-output-query evaluator | Correct / 192 | Candidate scores |
| --- | ---: | ---: |
| Familiar specialist, top 100 | 40 | 38,400 |
| Shifted specialist, top 100 | 39 | 38,400 |
| Pooled structural ranker, top 100 | 57 | 19,200 |
| Frozen dual-specialist confidence, top 100 | 64 | 38,400 |
| Fixed candidate mean, top 100 | 64 | 38,400 |
| Early stacked ranker, top 100 | 66 | 57,600 |
| Later stacked ranker, top 100 | 68 | 57,600 |
| Scrambled added feedback, top 100 | 63 | 57,600 |
| Duplicate early history, top 100 | 63 | 57,600 |
| Fixed dual, four selected tasks per bank widened to 200 | 66 | 57,248 |
| Fixed dual, top 200 everywhere | 68 | 76,112 |
| Later stack, top 200 everywhere | **73** | **114,168** |

The later top-100 stack tied dual top-200 at 68 with 18,512 fewer candidate scores, but it used 57,150 historical training labels and an extra model pass at inference. The near-matched-score fixed selective-width policy scored 66 using 57,248 candidate scores. Later stacked versus that policy was +2 with interval -4 to +8. These score counts exclude candidate generation, old ranking, training and 791,056 public candidate-output prediction cells, so they are **not** total-compute comparisons.

The predeclared evaluator-growth gate failed: later minus early was +2, only three winning banks, interval -2 to +6; later minus scrambled and duplicate was +5 each, but later minus fixed dual was only +4 with an interval crossing zero. The predeclared integration gate also failed. The 73/192 top-200 stack was a declared descriptive arm, without its own promotion gate. Its +5 versus later top-100 and +5 versus dual top-200 are useful exploratory evidence at a much larger score budget, not promotion evidence.

## Dissection of the evaluator

The [post-audit factorial diagnostic](analysis/candidate-stacking-factorial-diagnostic-20260918.json) separates ranker and shortlist effects. At top 100, switching from dual confidence to the later stack changed five wrong choices to correct and one correct to wrong, net +4. At top 200, the ranker edit yielded five wins and no losses, net +5. Widening with the dual route gave net +4; widening with the stack gave +5. The two-factor interaction was only +1. The combined 73 is therefore mostly the sum of two distinct improvements, with limited evidence of a special interaction.

Reachability sets the next target. Correct programs existed in 81/192 top-100 pools, 89/192 top-200 pools, and 94/192 full pools. The later stack chose 68 at top 100 and 73 at top 200, leaving 13 and 16 *ranking* misses in those reachable subsets. A retrospective per-task oracle over dual/stack and top-100/top-200 choices also scored 73. Routing among these four fixed actions has no target-bank upside beyond always applying the expensive later stack at 200. New candidate-ranking or candidate-generation edits are needed; another threshold on this action menu will not create intelligence growth.

## Seed and next experiment

Keep the audited dual-specialist top-100 confidence route as the supported zero-query seed for this AST mix. Store the stacked ranker and top-200 expansion as research edit types with full acquisition and inference costs. Do not promote the later checkpoint or the combined arm under this test. The next evaluator study should train a task-level ranking objective on verified candidates and test it against the candidate-level stack at the same top-200 pool and score budget. The improver study should then predict each new edit's *future held-out gain*, choose among ranker/search edits on an external admission bank, and test whether later inherited effect feedback creates a stronger child improver from the same frozen base on a second untouched bank.

Raw evidence: [development screen](analysis/candidate-stacking-development-20260918.json), [control training stats](analysis/candidate-stacking-controls-20260918/stats.json), [manifest](runs/candidate-stacking-feedback-transfer-20260918/manifest.json), [target outcomes](runs/candidate-stacking-feedback-transfer-20260918/results.json), [runner](candidate_stacking_feedback_transfer.py).
