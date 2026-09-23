# Sequential evaluator budget transfer: result

The learned second-query allocator improved over fixed entropy allocation at
the same output-query budget, but it did **not** pass the predeclared
evaluator-growth screen and did not beat the strongest fixed allocation.

## Question and setup

After one fixed weighted-entropy probe per task, should the evaluator spend a
second oracle output query on this task? The learned policy used first-answer
feedback and candidate-survivor features to predict the incremental benefit.
The second probe selection itself remained fixed weighted entropy. The
development source comprised 384 already inspected tasks; the transfer test
used six new 64-task AST banks, seeds 902123–902128. All methods used the same
candidate pools and first answer. Each allocation policy bought exactly 16
second answers per bank: 480 total output queries across 384 tasks.

| Policy | Correct / 384 | Output queries |
| --- | ---: | ---: |
| Initial ranker | 156 | 0 |
| One weighted probe per task | 239 | 384 |
| Random second-query allocation | 251 | 480 |
| Survivor-count allocation | 244 | 480 |
| Fixed entropy allocation | 261 | 480 |
| **Learned** second-query allocation | **269** | 480 |
| Fixed top-disagreement allocation | **270** | 480 |
| Two weighted probes on every task | 293 | 768 |

Candidate reachability was 338/384. Of the 54 tasks helped by a second
query, the learned allocation captured 30 with 96 extra queries;
top-disagreement captured 31 and entropy captured 22. A second query caused
no regressions on these 384 tasks. The two-query-on-all-tasks reference uses
288 more outputs than the allocation policies.

## Paired transfer test

Learned minus fixed entropy by bank was `[2, 0, -1, 2, 0, 5]`, eight tasks in
aggregate. It won three banks, tied two, and lost one. The exact six-bank
resampling 95% percentile interval for the mean difference was
`[-0.17, 3.00]` tasks per bank. The prespecified screen required wins on at
least four of six banks *and* an interval above zero; it failed.

Against the strongest fixed control, top-disagreement, the learned-minus-fixed
differences were `[1, -1, -3, 1, -2, 3]`, minus one in aggregate; the
bank-level interval was `[-1.83, 1.50]`. The learned rule is therefore an
interesting transferable competitor to one static allocation, not a
confirmed better evaluator. The reported development advantage at this
budget was learned 287 versus entropy 281/384, chosen after comparing
development budgets. The new transfer banks were not used to choose the
budget or coefficients and must not be reused as untouched confirmation.

## Measurement interpretation

First-answer feedback clearly improved within-task selection, and targeted
second queries gave 30 more correct decisions for the learned rule at the
matched 480-query budget. The strongest fixed allocation gave 31 more.
Accordingly, this tests both the value of feedback and the extra value of a
retained *learned* feedback policy. The first succeeded in this domain; the
second did not meet its gate. No improver checkpoint, change-utility
prediction, or child-improver growth was measured here.

All 384 cases passed an audit that regenerated tasks, reconstructed candidate
fit, first-answer features, frozen allocations, and final outcomes. Decisions
were saved before the separate scoring command used second answers and final
labels. A first preparation attempt failed on a missing minimax feature
before any records or scores were written; the empty directory was verified,
the code was fixed, and the run was prepared once successfully. The local
bank file is not independently access controlled, so the protection is
auditable code flow rather than physical oracle isolation.

The shared pool contained 31,866 candidates and required 254,928 candidate
executions to predict outputs on eight probe inputs. Successful preparation
took 127.3 seconds of wall time with eight workers; the failed preparation
also consumed candidate-generation compute and is an additional research
cost. Training reused the previous 384-task transfer bank and its oracle
labels. These costs must be charged before claiming net efficiency.

The next study should make the error family and candidate generator vary
prospectively. Retained policy growth requires beating the best fixed
allocation at matched resources on those new banks. Even then, a separate
same-base improver and child-improver comparison is required for recursive
intelligence growth.
