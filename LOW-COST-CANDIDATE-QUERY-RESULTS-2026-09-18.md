# Low-cost candidate-conditioned evaluator transfer

Status: **the 24-feature query evaluator passed the fresh cost and fixed-output-call gates; the later feedback checkpoint failed admission and child-growth gates.** The protected earlier cheap checkpoint remains the strongest tested budgeted policy on this fourth synthetic panel. Full independent candidate replay and child-decision reconstruction passed.

## Intervention and frozen test

The preceding E0 candidate-conditioned query evaluator used 26 public features. Two features checked whether the E0 top candidate agreed with E1 and 7-leaf candidate rerankers. These require two extra model prediction passes across the top-20 feature rows, although E0 alone determines the candidate order. Removing them leaves 24 features that depend only on the old and E0 orders, old scores, predicted outputs and public task context. The frozen implementation independently computes the cheap vector without reading E1 or 7-leaf orders, and verifies it equals the 26-feature vector with those two entries removed.

On opened development, cheap versus full scored 723 versus 724 in 24-bank source leave-one-bank-out evaluation, and 389 versus 387 on an already opened third panel. The latter was used only to choose a cost test. `EXPERIMENT-candidate-query-cost-transfer.md` froze the rule, source panels, new seeds 902546-902557, controls and gates before task generation or final scoring.

All seven policies used **the same E0 candidate order, probe and 96 total exact-output calls** across twelve new 48-task banks. Cheap initial had 1,152 earlier verified query-effect records; cheap later had 1,728. Scrambled and duplicate additional feedback, a 26-feature full model on the same 1,728 rows, an old 12-feature model on those rows, and the frozen incumbent were controls. The first six new banks were admission; the final six were protected transfer.

## Fresh results

| Policy | Admission / 288 | Protected transfer / 288 | All / 576 | Gain-forecast MSE |
| --- | ---: | ---: | ---: | ---: |
| E0, no calls | 161 | 166 | 327 | — |
| Frozen incumbent | 180 | 179 | 359 | 0.14353 |
| Old features, matched 1,728 records | 181 | 181 | 362 | 0.14505 |
| Full 26 features, matched 1,728 records | 185 | 185 | 370 | **0.13007** |
| Cheap initial, 1,152 records | **188** | 186 | **374** | 0.13083 |
| Cheap later, 1,728 records | 183 | **187** | 370 | 0.13137 |
| Scrambled additional records | 183 | 183 | 366 | 0.13656 |
| Duplicated earlier records | 184 | 184 | 368 | 0.13112 |

Cheap later **tied full matched-data at 370/576**, with paired interval [-4,+4], and its MSE differed by only +0.00130. It met the frozen noninferiority margin while saving two reranker prediction passes on each of 11,384 top-20 feature rows: **22,768 candidate-level model predictions** in a deployed implementation. Cheap later exceeded the frozen incumbent by **+11**, eight positive banks, two losing banks and paired exact bank-bootstrap interval **[+3,+20]**; its gain-forecast MSE was also lower. The declared fixed-output-call evaluator gate passed. These results support the **low-inference-cost feature representation** on this synthetic task contract.

Additional feedback did not improve the cheap evaluator checkpoint. Cheap later scored **183 versus cheap initial 188** on admission and was rejected before protected transfer. It gained only **+1** over initial on the six protected banks, two positive, one losing, interval **[-2,+4]**. The child-growth gate failed. Across all twelve banks, cheap initial selected 47 query fixes versus later 43, full matched 43 and incumbent 32. Unavailable hindsight could select 90 fixes at the same call budget, leaving regret of 43 for cheap initial. The extra 576 verified effects worsened its MSE slightly (0.13083 to 0.13137) and shifted some calls away from useful cases. More feedback is not automatically better feedback.

As a secondary diagnostic, the unchanged E1 candidate reranker scored 342 versus E0 327 with no calls, but its own incremental bank-win gate failed (six positive and three losing banks). The cheap E0 package scored 374 with 96 calls, above E1 plus the old common allocator at 371. These are different component comparisons; E1 remains unpromoted.

## Resource and verification limits

The fourth panel generated 99,632 base candidates and 35,214 additional AST candidates, rescored 11,384 top-20 entries, predicted 1,078,768 candidate/probe outputs, and took 301.8 seconds of preparation wall time (1,432.0 summed parallel candidate-generation seconds). The research oracle checked 134,846 final candidate labels. Every budgeted policy used 96 logical exact-output calls. The later model consumed 576 more historical verified task effects than initial; both require E0's previously acquired 11,282 candidate training labels. Source acquisition and model training remain part of the resource vector.

The offline harness computed E1 and 7-leaf predictions for every policy so it could replay all counterfactuals. The **22,768 saved predictions are a deployable work count, not a measured wall-time saving**. A full end-to-end runtime comparison and transfer to changed generators or cue-disrupted tasks remain open. The same synthetic generator across the four panels limits generality.

The independent audit rebuilt 864 earlier candidate-model source tasks, 16,948 source labels and four models; regenerated all 576 new tasks/pools, checked 11,384 target top-20 rerankings, 1,078,768 output predictions, 12 allocations and 134,846 final candidate labels. A separate check refit all seven query policies, reconstructed the 24-feature vectors and rechecked 4,032 target child decisions. Both passed. Machine evidence: `runs/candidate-query-cost-transfer-20260918/cost_results.json`, `runs/candidate-query-cost-transfer-20260918/audit.json` and `runs/candidate-query-cost-transfer-20260918/cost_children.json`.

**Seed decision:** preserve the cheap initial 1,152-record evaluator checkpoint as the best observed protected policy for this contract; the cheap feature representation passed the cost-aware transfer. Keep the 1,728-record update in shadow because admission and child-growth failed. The improver's next edit should decide whether to accept, downweight or reject new effect batches using evidence from disjoint admission banks, and it must prove that decision helps a later child on another untouched bank. A positive evaluator result does not yet establish a positive feedback loop.
