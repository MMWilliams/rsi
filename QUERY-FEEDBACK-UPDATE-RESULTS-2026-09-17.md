# Incremental query-value feedback: third-bank transfer

## Decision

**Reject the incremental update.** Adding 192 verified query-effect tasks to the 18-feature ridge evaluator did not improve query allocation on six untouched banks. At exactly 95 external output queries per policy, the updated model scored **173/192** versus **175/192** for its previous 192-task checkpoint. It tied on five banks and lost two tasks on one; the exact six-bank resampling 95% interval for updated minus previous was **−6 to 0**. It also trailed fixed top disagreement and the duplicated-prior control at 174/192. The 192-task reconstruction audit passed.

## Controlled comparison

All policies shared the temperature-0.25 ranker, common candidate pools, identical 95-query live budget, maximum-entropy probe selection among the top 16 programs, full-pool filtering after each oracle output, and 15 separate final examples. Candidate reachability was 190/192. The previous model learned from 192 inspected tasks. The update added another 192 task-level query effects, holding the ridge penalty and feature schema fixed. Scrambled update preserved each new bank's gain prevalence but shuffled effects across its tasks; duplicated prior repeated the old rows to match the updated row count without new information.

| Policy | Correct / 192 | Live output queries |
| --- | ---: | ---: |
| Sharp ranker, no query | 155 | 0 |
| Scrambled update | 171 | 95 |
| **Genuine feedback update** | **173** | **95** |
| Duplicated prior | 174 | 95 |
| Fixed top disagreement | 174 | 95 |
| Previous learned model | **175** | **95** |

Whole-bank cross-validation on the two inspected source panels had scored 174/192 on the first and 172/192 on the second, but did not reveal a positive update effect. On the new bank the updated policy allocated 38 queries to mutation tasks versus 27 for the previous model. The sharp ranker already solved 49/66 new mutation tasks without a query, compared with 34/66 on the bank whose feedback prompted that shift. This is consistent with context difficulty changing across banks; it does not prove that family allocation alone caused the regression.

The added feedback required counterfactual oracle output and final-outcome evaluation on 192 development tasks, separately from the common 31,500 candidate labels used to train the ranker. The controls matched live queries; historical acquisition cost is additional for the updated model. The audit regenerated every candidate pool, recomputed public choices and all model predictions, verified allocations, and replayed every oracle-conditioned final result.

Protocol: `EXPERIMENT-query-feedback-update-transfer.md`. Update construction: `query_feedback_update_development.py`, `analysis/sharp-query-feedback-updated.json`. Transfer, audit and data: `query_feedback_update_transfer.py`, `audit_query_feedback_update_transfer.py`, `runs/query-feedback-update-transfer-20260917/`.

## Implication for the seed improver

The failure is not a lack of solver headroom: 190 of 192 candidate pools contained a correct program. It is a failure to predict where another oracle output helps on a changing bank. The fixed top-disagreement policy remains the supported 95-query control. A later improver should adapt its allocation from protected within-bank feedback, keep a rollback gate against the fixed policy, and be tested as a parent of a child policy. More historical query-effect labels with the same global ridge rule did not compound.
