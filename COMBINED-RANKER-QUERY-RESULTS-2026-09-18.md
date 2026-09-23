# E1 reranking combined with candidate-conditioned query selection

Status: **integrated E1-over-E0 package gate failed; later-child improver-growth gate failed.** E1's no-query checkpoint passed its gate on this individual fifth panel, but that did not carry through the matched learned-query package. Full independent candidate replay and child-decision reconstruction passed.

## Why test the combination

The E0 reranker and 24-feature candidate-conditioned query allocator are the strongest supported low-cost components on the six-mechanism synthetic string/program contract. E1 learned from 288 more verified candidate-training tasks than E0 and often ranks more correct programs first, but its earlier incremental gates were unstable. The query sensor's value falls as the ranker fixes some of the same errors. A package must therefore be judged after **each ranker gets a query model trained for its own candidate order**, not by adding separate component gains.

Across four opened audited panels, 48-bank leave-one-bank-out scoring of matched 24-feature mechanism-interaction query models gave E1 **1,517/2,304** versus E0 **1,488/2,304** at eight output calls per bank, paired interval [+10,+48]. A task-level ranker router screened separately scored only +8 over fixed E1 across 2,304 zero-query tasks, interval touching zero, so it was not carried forward. The package result remained a source hypothesis. Protocol: `EXPERIMENT-combined-ranker-query-transfer.md`; development: `analysis/combined-ranker-query-development-20260918.json` and `analysis/joint-ranker-route-development-20260918.json`.

## Fifth untouched panel

The new panel used seeds 902558-902569, 576 tasks, identical candidate pools, fixed probe indices and 96 logical output calls per budgeted policy. E0 and E1 query models used the same 24-feature rule, model class and 2,304 earlier verified task-effect records; features were recomputed relative to each ranker's order. Their only candidate-model acquisition difference is E1's 5,666 additional historical candidate labels. Models, forecasts and calls were frozen before target final labels opened.

| Package | Correct without calls / 576 | Correct with 96 calls / 576 | Selected query fixes | Gain-forecast MSE |
| --- | ---: | ---: | ---: | ---: |
| E0 + old allocator | 344 | 364 | 20 | 0.13729 |
| E1 + old allocator | **356** | 375 | 19 | 0.12853 |
| E0 + matched cheap query learner | 344 | 380 | **36** | 0.12372 |
| E1 + matched cheap query learner | **356** | **385** | 29 | **0.11251** |
| E1 + earlier 1,152-effect query learner | **356** | **386** | 30 | 0.11376 |

E1 exceeded E0 by **+12** zero-query top choices, with nine positive banks, one losing bank and interval [+3,+21] under the original candidate-checkpoint gate. Under the same frozen old call locations it exceeded E0 by +11. With matched learned query models, E1 exceeded E0 by only **+5**, with four positive and four losing banks and paired exact bank-bootstrap interval **[-4,+15]**. The preregistered package gate required at least +8, eight positive banks, no more than two losses and positive lower endpoint. It failed. The opened-source +29/2,304 package signal therefore did not establish fresh integrated superiority.

The mechanism is visible in the paired query effects: E0's trained allocator fixed 36 choices, E1's fixed 29. E1's improved ranking left fewer errors for a first output call. At the same eight-call budget, unavailable hindsight could fix 85 E0 choices but only 76 E1 choices. E1 had lower gain-forecast MSE yet a smaller absolute query opportunity. Evaluator calibration, selected marginal gain and final package correctness must be reported separately.

## Incremental E1 improver checkpoint

The E1 initial query child used the first 1,152 task effects; later used all 2,304. A scrambled added-history child and duplicated-history child each had 2,304 rows. The first six fresh banks were admission; the final six were protected transfer.

| E1 query child | Admission / 288 | Protected transfer / 288 | All / 576 |
| --- | ---: | ---: | ---: |
| Earlier 1,152 effects | **192** | 194 | **386** |
| Later 2,304 effects | 189 | **196** | 385 |
| Scrambled additional effects | **192** | 193 | 385 |
| Duplicated earlier effects | 190 | 194 | 384 |
| E1 with old allocator | 187 | 188 | 375 |

Later failed admission, **189 versus earlier 192**. It gained only +2 on protected transfer, in two of six banks, with interval [0,+4]. The child-growth gate failed. The protected procedure retains the earlier E1 query checkpoint as a shadow comparator; the overall E1 package remains unpromoted because the matched package gate failed. Larger history improved E1's forecast MSE (0.11376 to 0.11251) but reduced selected query fixes (30 to 29), again showing why forecast error alone cannot be the intelligence outcome.

## Costs and audit

The fifth panel generated 100,196 base candidates and 34,074 additional AST candidates, rescored 11,234 top-20 entries and predicted 1,074,160 candidate/probe outputs. Preparation took 310.4 seconds wall time and 1,447.9 summed parallel candidate-generation seconds. The research oracle checked 134,270 target candidate labels. Each budgeted package used 96 logical exact-output calls. Both matched query models used 2,304 verified historical E0/E1 task effects; E1's candidate model also required 5,666 candidate labels beyond E0's 11,282. The offline harness computed all counterfactuals, so this is not a measured end-to-end runtime comparison.

The independent audit retrained four original candidate models from 864 source tasks and 16,948 source labels; regenerated all 576 target tasks/pools; checked 11,234 rerankings, 1,074,160 predicted output cells, 12 allocations and 134,270 final labels. The child check reconstructed 2,304 historical source tasks and 4,032 target child decisions. Both passed. Machine evidence: `runs/combined-ranker-query-transfer-20260918/combined_results.json`, `runs/combined-ranker-query-transfer-20260918/audit.json`, `runs/combined-ranker-query-transfer-20260918/combined_children.json`.

**Seed decision:** retain the protected E0 plus 24-feature query evaluator as the supported integrated system on this synthetic contract. Keep E1 and its earlier query child in shadow. The next improver needs to predict **package-level marginal value**, including how a ranker edit changes sensor opportunity and cost, and then accept or reject edits on protected tasks. A stronger artifact or isolated ranker is not yet a stronger inherited improver.
