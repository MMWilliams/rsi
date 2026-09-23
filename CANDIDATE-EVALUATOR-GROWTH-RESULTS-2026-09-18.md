# Candidate-level evaluator feedback on fixed pools

Status: **strong fresh fixed-pool evaluator gain; later-checkpoint promotion gate failed.** The independent full replay passed in `runs/candidate-reranker-transfer-20260918/audit.json`.

## Intervention and measurement

The old public-block/AST replay ranker generated and ordered the same full candidate pools for all policies. New evaluators rescored only its top 20 programs using 175 public structural features, the old score/rank, pool size and public mechanism block. An exact external interpreter supplied source correctness labels on final hidden examples; neither hidden outputs nor final labels entered target features. The models placed their reordered top 20 first and left the remaining pool in old order. Generator reachability is therefore fixed.

E0 was a 15-leaf boosted candidate classifier trained on 576 prior tasks and 11,282 verified top-20 candidate labels. E1 used the same algorithm with 288 additional prior tasks, 864 tasks and 16,948 labels total. A 7-leaf same-data model and a within-task label-scrambled same-data model controlled capacity and inheritance. The old ranker was the no-edit control. All models, hashes, target task IDs and scoring rules were frozen before generating seeds 902510–902521. Protocol: `EXPERIMENT-candidate-reranker-transfer.md`.

## Fresh result on 12 mixed banks

| Evaluator | No-query correct / 576 | Correct with the same 96 output calls |
| --- | ---: | ---: |
| Old ranker | 284 | 321 |
| E0 reranker | 323 | 356 |
| E1 reranker | **334** | **358** |
| 7-leaf control | 309 | 339 |
| Scrambled-label control | 218 | 259 |

On the same pools, E0 minus old was **+39**, positive in all 12 banks, exact paired bank-bootstrap interval **[+27,+52]**. E1 minus old was **+50**, positive in all 12, interval **[+33,+68]**. This is a substantial evaluator edit: it improves which available program is selected, with no added output calls. With the old frozen query allocator and the same probe index for every policy, E1 minus old remained +37, positive in 11 banks and no losses, interval [+25,+50].

The primary incremental comparison was E1 minus E0 at zero queries: **+11**, seven positive banks, two losing banks, interval **[+2,+21]**. The preregistered promotion gate required eight positive banks and therefore failed. Under the common eight-call budget, E1 exceeded E0 by only +2, interval [-6,+10]. Additional candidate-level feedback improved top-choice performance in this trial, but reliable improvement of the integrated budgeted evaluator is not established by the gate.

The full pools contained correct candidates for 492/576 tasks. A correct candidate appeared in the old ranker's top 20 for 447/576. E1 selected 334 without a query. The remaining 113 top-20 reachable misses show further candidate-evaluation headroom; the 45 tasks reachable only below rank 20 require a different search or shortlist edit.

The typed task ledger separates the improvement from the sensor's marginal value. E1 gained on 63 tasks and harmed 13 relative to the old zero-query ranker, net +50. E1 versus E0 gained on 19 and harmed eight, net +11. A single output call on **every** task gained 118 choices over old zero-query ranking, but only 86 over E1 zero-query ranking. At the fixed eight-call locations, old gained 37 from the sensor, E0 gained 33 and E1 gained 24. Better ranking had already recovered some choices that a query would otherwise fix; this explains why E1's +11 no-query increment became only +2 under the common budget. See `analysis/candidate-edit-effect-ledger-20260918.json`.

The exact oracle checked 135,006 target candidate labels for research scoring. Preparation generated 101,382 base candidates plus 33,624 extra AST candidates, rescored 11,450 top-20 entries and predicted 1,080,048 candidate/probe outputs. Preparation wall time was 306.8 seconds and summed parallel candidate generation time was 1,458.5 seconds. Each budgeted policy used 96 true output calls. Source label acquisition and model fitting are separate from those live-call budgets.

The independent auditor reconstructed all 864 source tasks, rechecked 16,948 source candidate labels and public feature rows, and retrained all four models. It regenerated all 576 fresh tasks and pools, checked all 11,450 top-20 rescored entries, 1,080,048 predicted output cells and 12 frozen allocations, then replayed 135,006 final labels and 180 bank-policy scores. All checks passed.

## Mechanism effects and next integration

On the fresh 96-task-per-mechanism panels, E1 versus old gained +22 transformation, +7 AST, +12 novel-operator, +8 stack and +4 mutation correct choices, while self-edit lost three. The same self-edit direction occurred on two other opened 576-task panels, by one task each. A public self-edit fallback to the old ranker would score 337 rather than 334 on the current opened bank; this gate was chosen after inspecting results and needs a fresh frozen test. See `analysis/candidate-reranker-family-development-20260918.json`.

The fixed E0 reranker is the strongest newly supported candidate-evaluator component relative to the old ranker. E1 remains an unpromoted later checkpoint despite its positive total. The next seed-improver test should let the improver propose and verify a reranker edit alongside task-level query allocation and conditional search edits, then measure whether inherited effect knowledge helps a later parent create a better **child improver** from an identical base on untouched cases. A better child evaluator alone does not prove that recursive endpoint.

The tested task-level action menu now has material but bounded headroom. On this opened bank, the best fixed no-query candidate ranker scored 334, an oracle choosing among old/E0/E1/7-leaf rankers for each task scored 351, and joint hindsight choosing a ranker plus eight query locations per bank scored 423 versus E1's fixed eight-call 358. These use unavailable labels and show the space in which a future improver could act; see `analysis/candidate-edit-catalog-headroom-v2-20260918.json`.

Evidence: `analysis/candidate-reranker-development-20260918.json`, `analysis/candidate-reranker-top20-cache-20260918/`, `runs/candidate-reranker-transfer-20260918/`, `analysis/candidate-reranker-family-development-20260918.json`, and `analysis/candidate-edit-effect-ledger-20260918.json`.
