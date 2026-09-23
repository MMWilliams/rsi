# Learned verifier-query value: matched-budget transfer

## Decision

**Do not promote the learned query allocator.** On six untouched 32-task banks, it solved **172/192** at 95 external output queries versus **169/192** for the strongest fixed top-disagreement control at the same 95 queries. It won four banks, tied one, and lost one; the exact six-bank resampling 95% interval for its three-task edge was **−1 to +6**. It failed the predeclared five-bank and positive-interval gates. The reconstruction audit passed.

## Setup and result

All policies shared the same frozen temperature-0.25 ranker, one visible example, candidate pools from two sources capped at 128 each, eight public probe inputs, and 15 final examples. The 18-feature ridge allocator was trained on 192 previously inspected tasks to predict whether one exact oracle output would improve the ranker's choice. Its penalty of 10 was selected in whole-bank cross-validation, where it scored 174/192 versus 172/192 for fixed top disagreement. The full model and query plans were frozen before fresh oracle outputs were opened.

Each queried task used the public-input probe that maximized output entropy among the ranker's top 16 candidates. After receiving one oracle output, the evaluator filtered the full pool to matching programs and chose the highest-ranked survivor. Every active policy received exactly **95** output queries across the 192 fresh tasks.

| Policy | Correct / 192 | Output queries |
| --- | ---: | ---: |
| Sharp ranker, no query | 138 | 0 |
| Deterministic random allocation | 156 | 95 |
| Fixed uncertainty allocation | 161 | 95 |
| Fixed top disagreement | 169 | 95 |
| Learned query value | **172** | 95 |

Candidate reachability was **190/192**. Learned-minus-fixed differences by bank were **0, +1, +1, −1, +1, +1**. The large gain over no-query reflects purchased oracle information; the small uncertain difference from fixed top disagreement is the test of whether the learned evaluator allocated that information better. The fixed rule remains the supported cost-aware seed component at this budget.

The 192-task audit regenerated all candidate pools, recomputed public model choices and query allocations, and verified every oracle-conditioned choice and final outcome. It passed. The source feedback used to train the allocation model required one counterfactual output query per development task plus verified final choices, in addition to the shared 31,500 labels that trained the ranker. The query outputs and finite final examples measure this synthetic domain; they do not establish universal program correctness.

Protocol: `EXPERIMENT-sharp-query-value-transfer.md`. Source analysis and frozen model: `sharp_query_value_development.py`, `analysis/sharp-query-value-development.json`, `analysis/sharp-query-value-frozen.json`. Transfer runner, audit and data: `sharp_query_value_transfer.py`, `audit_sharp_query_value_transfer.py`, `runs/sharp-query-value-transfer-20260917/`.

## Improver implication

The complementary context evaluator had an oracle union of 161/192 with the sharp ranker on an inspected bank. A plain score blend never beat the sharp ranker, and a one-query two-evaluator arbitrator reached 161/192 using 95 queries. Querying and reranking the full pool reached 166/192; a fixed top-disagreement allocation reached 172/192 at the same budget. Thus the strongest integration tactic observed so far is a cheap static sensor rule, not a learned selector over the two models. A seed improver should retain this rule as a control while searching for genuinely new evaluator edits and testing their child-improver effects.
