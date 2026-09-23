# Incremental evaluator feedback: integration and fresh transfer

Status: **focused feedback rejected; no evaluator or improver growth established by this update.** The independent regeneration audit passed in `runs/focused-feedback-transfer-20260918/audit.json`.

## Question

The current mixed-task evaluator already uses a feedback-trained model to allocate eight exact output calls per 48-task bank. Does additional verified feedback make that evaluator better at choosing calls, rather than merely improve the final solver score through a wider search pool?

All claims here concern a synthetic six-mechanism string/program benchmark. Final correctness is judged by an exact external interpreter on hidden examples. The evaluator cannot change that oracle. Candidate reachability, pre-query ranker quality, query utility and training quality are recorded separately.

## Opened-bank integration check

`joint_width_query_development.py` applied two earlier frozen cross-family query models to three **already opened** AST-width panels. These are development results, not a fresh promotion test. On the twelve opened transfer banks (576 tasks), the ridge-100 allocator made **zero AST calls** regardless of width policy:

| AST width choice | Correct with eight cross-family calls | Correct if every task receives a call | No-query correct |
| --- | ---: | ---: | ---: |
| Base pool | **343** | 408 | **306** |
| Random four AST tasks widened | 341 | 412 | 304 |
| Low score-gap four widened | 339 | 416 | 302 |
| All eight widened | 339 | **418** | 302 |

Widening expands what the AST branch can solve when its outputs are checked, but this particular eight-call allocator spends its calls elsewhere. The widened branch then relies on its weaker zero-query ranking. This is a measurable interaction between search and evaluation, not evidence that widening is generally harmful. The development simulation computed 1,034,928 additional non-AST predicted output cells across its 18 banks; deployed cost and measured research-harness work are distinct.

## Opened-bank evaluator checkpoint replay

`incremental_query_evaluator_development.py` froze one interaction ridge-100 training rule and replayed E0 after 576 source tasks, E3 after three feedback banks, and E6 after six. All models faced the same twelve previously opened transfer banks, with 96 calls total. Feedback used **288 full counterfactual task labels**, meaning both no-query and one-query results were known even where the old policy did not query.

| Checkpoint | Correct / 576 | Marginal-gain forecast MSE | True selected query gain |
| --- | ---: | ---: | ---: |
| E0 | **342** | **0.14965** | **38** |
| E3 | 339 | 0.14976 | 35 |
| E6 | 341 | 0.15022 | 37 |
| Scrambled E6 | 336 | 0.15301 | 32 |
| Duplicated-source E6 | 341 | 0.15062 | 37 |

E6 minus E0 was -1 task across twelve banks, exact bank-bootstrap interval [-4,+2]. E0 and E6 chose 87 of the same 96 calls. The oracle's best eight calls per bank would have yielded 90 true marginal gains, so query placement has headroom. That oracle comparison uses labels unavailable to the policy.

A development screen of six researcher-specified weights found that giving weight four to the 25 feedback tasks where E0 bought a useless call scored 186 versus E0's 182 on opened panel A and tied 160 on opened panel B. This was only a candidate intervention because both panels had already been inspected.

## Fresh focused-feedback transfer

Protocol: `EXPERIMENT-focused-feedback-transfer.md`. Seeds 902486–902497 were generated after the protocol and E0, ordinary E6, focused E6 and scrambled E6 model parameters were frozen. The same full-width AST pools, ranker, sensor and eight-call budget were used for all policies. All 576 task allocations were saved before the exact oracle results were opened.

| Policy | Correct / 576 | Forecast MSE for query gain |
| --- | ---: | ---: |
| E0, no new feedback | **345** | **0.14873** |
| Ordinary E6 | 343 | 0.15083 |
| Focused E6 | 340 | 0.15111 |
| Scrambled E6 | 340 | 0.15102 |
| Fixed transform + mutation calls | 334 | — |
| Deterministic random calls | 322 | — |

The no-query system scored 307. A call for every task scored 427 but used 576 calls rather than 96. Hindsight placement of eight calls per bank would have scored 395. The candidate pools contained a correct candidate for 505 tasks. Focused E6 minus E0 was **-5**, with two positive banks, four losing banks, and exact bank-bootstrap interval **[-13,+2]**. The preregistered promotion gate failed.

Focused E6 kept 76 of E0's 96 calls. Its shifts gained two tasks in self-edit cases but lost seven in stack cases; AST remained unqueried by both. This explains the net -5 and shows that correcting earlier false calls did alter the evaluator, but in the wrong direction on new tasks. Forecast error rose as well.

The fresh run generated 101,224 base candidates plus 34,888 extra AST candidates, predicted 1,088,896 candidate/probe outputs, and externally checked 136,112 candidate final labels for research scoring. Preparation wall time was 316 seconds; summed parallel generation CPU time was 1,552 seconds. Each deployed policy is charged 96 true output calls. The six-bank feedback source itself required 67,052 candidate final labels and 536,416 predicted output cells, in addition to the earlier 576-task source. These acquisition costs must be amortized before claiming any practical benefit.

The independent auditor rebuilt all four source models, regenerated all 576 tasks and candidate pools, rechecked 1,088,896 predicted output cells and 72 frozen bank-policy allocations, and replayed all 136,112 final candidate labels and 72 bank-policy scores. It also recomputed the forecast errors and promotion gate. All checks passed.

## Decision and next measured step

Keep E0 as the current evaluator checkpoint for this exact task contract. Do not promote ordinary or focused E6. Do not call the failed update an improving improver: the focused weighting rule was designed by the researcher and its fresh child performed worse. The stronger scoped result remains the earlier cross-family allocator versus fixed call schedules; repeated feedback has not yet made that allocator better.

The next intervention should target **decision-relevant feedback** and the failure to allocate calls across mechanism families. Train on the marginal value of a call at the allocation boundary, retain counterfactual negatives, and assess change in held-out query regret and forecast error at E0/E3/E6. Before any new promotion test, freeze a truly new source/holdout sequence, an explicit source-acquisition budget, and an unchanged-policy fallback. A separate same-base I0/I3/I6 test is still needed to show that a later improver creates a better child improver.

Evidence: `analysis/joint-width-query-{admission,a,b}-20260918.json`, `analysis/incremental-query-evaluator-development-20260918.json`, `analysis/incremental-query-evaluator-diagnostics-20260918.json`, `analysis/focused-feedback-development-20260918.json`, and `runs/focused-feedback-transfer-20260918/`.
