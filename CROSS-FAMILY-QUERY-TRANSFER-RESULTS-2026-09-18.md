# Feedback-trained query allocation across six mechanisms

## Decision

**Promote the cross-family value model as a scoped evaluator allocation component.** On twelve untouched 48-task mixed banks, it selected **341/576** correct programs using **96 true output calls**. The strongest fixed eight-call schedule (four transformation and four mutation tasks per bank) selected **322/576**. Paired differences were +2,−1,+3,+3,+2,+1,−1,+2,+3,+3,+2,0: nine positive banks, two losses, one tie. The exact bank-bootstrap 95% interval for the twelve-bank sum was **+9 to +28**. Both separately frozen six-bank panels gained: **180 versus 170** and **161 versus 152**. The predeclared transfer gate passed, and the full reconstruction audit passed.

This is a **feedback-trained evaluator decision**: it learns where an external output query is likely to change a wrong program choice. It is not a demonstrated improvement in the rule that improves future evaluators, nor a later-parent-to-better-child improver result. Its source feedback cost is substantial and is separate from the matched 96-call transfer budget.

| Policy on the same 576 tasks | True output calls | Correct |
| --- | ---: | ---: |
| No query | 0 | 294 |
| AST-only fixed | 96 | 320 |
| Transformation-only fixed | 96 | 320 |
| Mutation-only fixed | 96 | 319 |
| Transformation/mutation 4+4 fixed | 96 | **322** |
| Family-balanced fixed | 96 | 315 |
| Deterministic random fixed | 96 | 316 |
| Learned family-frequency values | 96 | 320 |
| Basic ridge-10 | 96 | 339 |
| Family ridge-10 | 96 | 337 |
| Interaction ridge-10 | 96 | 340 |
| **Prespecified interaction ridge-100** | **96** | **341** |
| One query on every task | 576 | 431 |
| Hindsight best eight per bank | 96 | 390 (unavailable oracle) |

The selected model uses mechanism, frozen candidate rank scores, and candidate-predicted outputs on eight probe inputs. The implementation encoded mechanism with the benchmark generator's `family` field. A separate public-feature audit proved that this field mapped one-to-one to the **visible Unicode block on all 576 source and 576 target tasks**, and replacing it with that block reproduced all five model fits and all 60 learned bank allocations. The model was fitted to **576 previously inspected verified task effects** using ridge penalty 100; the penalty and feature interactions were chosen on leave-one-bank-out development, where it scored 342/576 versus transformation-only at 330. Both fresh panels used the same generator, evaluator, candidate pools, top-20 entropy probe selector and exactly eight queries per policy. Transfer when that visible cue is absent or misleading remains untested.

The learned policy spent its 96 calls on **37 transformation, 22 mutation, 24 stack and 13 novel-operator** tasks; it selected no AST or self-edit tasks on these banks. Those calls produced **47 newly correct choices**: 11, 15, 15 and six by family respectively. The AST-only fixed schedule produced 26. This is a task-level allocation gain beyond simply learning the average benefit of each family. Its probability-style query-gain forecasts had clipped Brier error **0.1616** and correlation **0.333** with realized gains; family-frequency predictions had error **0.1829** and correlation **0.040**. The interaction ridge-10 variant calibrated slightly better (Brier 0.1578) but selected one fewer correct task, so superiority among the learned variants is not established.

Candidate reachability was **501/576**. One query on every task improved 137 choices and harmed none in this sample, reaching 431 at six times the oracle-call cost. A hindsight allocator with each task's true outcome would reach 390 at the same 96 calls; the 49-task gap is diagnostic remaining headroom, not a deployable policy. The learned model's improvement over fixed schedules is therefore real within this synthetic distribution but far from the oracle bound.

## Cost and verification

Training acquired 576 historical task effects. A live acquisition of those effects would require **576 true probe outputs**, plus external final-correctness labels and candidate work. The two inspected source panels computed **1,106,512 candidate-predicted probe outputs**. The fresh transfer computed **1,067,008** more; generating its candidate pools took **317.5 seconds wall time** across the two panels and **1,457.4 summed worker seconds**. The learned policy must predict outputs for all tasks to allocate the bank budget, while a fixed family schedule can avoid some of that inference. Equal oracle-call counts are **not equal total compute**.

The audit retrained all five source models, regenerated **576 tasks**, **99,772 base candidate entries** and **47,226 wide AST entries**, checked all **1,067,008 predicted output cells**, rebuilt every rank/feature/allocation, and re-evaluated **133,376 final candidate labels** and all 132 bank-policy scores. Both panels passed before the combined summary was accepted. The additional public-feature replay passed as `audit_public_features.json`. Correctness is agreement on fifteen held-out examples in a synthetic string-program language, not universal program equivalence.

## Incremental feedback pilot and next gate

An **inspected** pilot added panel A's 288 verified effects to the source table and applied the updated model to panel B. It did **not** improve final choices: old and updated both scored **161/288**. The updated model's query-gain Brier error improved from **0.1652 to 0.1612**; a scrambled update scored 156 and a duplicated-source control 159. Panel B labels were already open when this pilot was designed, so it is development evidence only. Better forecast error without better choices does not establish improver growth.

The next protected test must compare initial and feedback-updated allocator checkpoints on **another untouched mixed bank**, with scrambled/duplicate-history and strongest fixed controls at equal 8-call inference budgets while charging the extra acquisition. Beyond that, a seed improver must choose and integrate edits across ranker training, search coverage, external sensors and rollback, then show that a later parent produces a better child improver on a second untouched bank. This result promotes one evaluator component, not the whole recursive loop.

Protocol: `EXPERIMENT-cross-family-query-transfer.md`. Development: `cross_family_probe_development.py`, `cross_family_query_value_development.py`, `analysis/cross-family-query-value-development.json`. Runner and auditor: `cross_family_query_transfer.py`, `audit_cross_family_query_transfer.py`. Frozen data: `runs/cross-family-query-transfer-20260918/`. Inspected update pilot: `cross_family_feedback_update_development.py`, `analysis/cross-family-feedback-update-development.json`.
