# Evaluator and improver edit-space decision

Status: **development synthesis, not a new positive RSI result.** This decision uses audited fresh runs plus post hoc analysis of their now-opened banks. The project goal remains to produce a better evaluator and a later improver that creates a better child improver from the same base.

## What a good evaluator must do here

The evaluator has two distinct jobs on a fixed candidate pool. First, rank candidate programs so its top choice is correct when the pool contains a solution. Second, predict the **marginal value of one exact output call** well enough to choose eight of 48 tasks. More accurate average gain probabilities are insufficient if the eight selected calls have lower realized gain. Report top-choice correctness, reachable-but-missed tasks, forecast Brier error, selected marginal gain, regret against unavailable eight-call hindsight, harms, bank uncertainty and all candidate/prediction/query costs separately.

The current full-width AST/replay ranker/public-block route/top-20 sensor is the supported fixed system. The cross-family eight-call allocator is the strongest confirmed feedback-trained component relative to fixed schedules, but its later feedback updates have failed their growth gates. On one fresh 576-task test, focused feedback scored 340 versus early E0 345; on another, pairwise P18 scored 339 versus same-rule P0 335, interval [-3,+11], and matched-data ridge-100 343. Both runs passed independent full replay. The ridge-100 checkpoint is best observed on the second run but its +5 versus E0 has interval [-1,+12], so it is not promoted as a stable improvement.

## What the action-space bounds say

| Action an improver could choose | Opened-bank headroom at the declared eight-call budget | Implication |
| --- | ---: | --- |
| Choose one entire evaluator policy per bank from the tested menus | +5 and +8 over each menu's best fixed policy on two separate 576-task runs | Too little headroom for a strong improver claim. |
| Choose top-20 or minimax sensor per queried task | +6 over top-20-only hindsight across 30 banks / 1,440 tasks | Sensor switching is a small secondary edit. |
| Add a second query where useful | +5 over one-query hindsight across the same 30 banks | Second-query learning is a small secondary edit. |
| Jointly choose four AST width expansions and eight queries | +10 over random-four width with hindsight query placement across 30 opened banks | AST width matters, but the tested selective-width choice has modest headroom and substantial candidate cost. |
| Place the first eight calls individually with hidden-label hindsight | +50 and +48 over the best fixed policies on two recent 576-task runs | Task-level call placement is the largest measured evaluator decision gap. |

These figures are **unavailable-label hindsight comparisons**, not deployed gains. Their task sets differ, so the rows should not be added. The bounds are conditional on the tested action catalogs; a genuinely new search or evaluation edit can expand the reachable frontier.

## Development-only model screens

On three already opened mixed panels, a small nonlinear classifier sometimes reduced Brier error without improving the top-eight choice. For example, a shallow boosted model reduced Brier from E0's 0.1523 to 0.1497 on a 576-task panel, yet selected 333 correct outcomes versus E0's 338. More flexible trees and forests did not consistently beat ridge or pairwise allocation. See `analysis/nonlinear-query-value-development-20260918.json`.

A ridge-anchored pairwise correction aimed at false selected calls and missed positive calls also failed: across the three opened panels, the tested corrections scored 313–329, 318–330 and 304–308, versus their ridge controls at 341, 344 and 343. They shifted 41–95 of 96 calls to AST in those panels. The attempted correction was not a safe improvement to deploy. See `analysis/residual-query-ranker-development-20260918.json`.

This distinguishes **forecast quality** from **decision quality** and identifies mechanism shift as a failure mode. A policy update should be evaluated on actual allocated-call utility and mechanism allocation, not accepted because loss or calibration improved on the training distribution.

## What a good improver must prove

An improver is the policy that proposes, tests, accepts and integrates changes to search, ranking, sensing and query allocation. Its transferable state should include edit types, public-context conditions, verified effect estimates, uncertainty, costs and descendant effects. The external oracle and holdout banks stay outside its write access. Its accepted changes must pass deterministic replay, budget accounting and a protected admission gate.

The primary recursive comparison is **later-parent child minus earlier-parent child**, each created from an identical frozen improver and solver base with the same new feedback and proposal budget. The later child must then make better improvement choices on a second untouched bank than the earlier child, scrambled/empty inheritance controls and the strongest fixed matched-data edit rule. A better final solver or a better evaluator checkpoint alone does not discharge this test. Current experiments have not passed it.

## Provisional seed and next experiment

Retain the verified candidate journal, public-block ranker route, AST replay/wide branch, exact top-20 output sensor, protected early cross-family eight-call evaluator and typed effect ledger. Keep unpromoted learned checkpoints in shadow. The next edit catalog should let the improver make **task-level** query allocation and conditional search/ranker choices, rather than select one policy for a whole bank. For every proposal, store a paired same-base effect vector: reachability, top-choice correctness, selected query gain, false accepts, candidate and prediction work, output calls, harm, and downstream child-improver gain.

Before another large confirmation run, the implementation should demonstrate on opened banks that the new edit catalog has materially more hindsight headroom than the current +5/+8 whole-bank menus, while charging its extra compute. Then freeze source, admission, child-creation and second-bank transfer separately and run the full parent-to-better-child test. If the catalog still has little headroom, expand edit types rather than tuning another learner over the same narrow choices.

Evidence: `EVALUATOR-FEEDBACK-GROWTH-RESULTS-2026-09-18.md`, `PAIRWISE-EVALUATOR-GROWTH-RESULTS-2026-09-18.md`, `analysis/edit-catalog-headroom-20260918.json`, `analysis/task-edit-catalog-bounds-20260918.json`, `analysis/nonlinear-query-value-development-20260918.json`, and `analysis/residual-query-ranker-development-20260918.json`.

## Subsequent candidate-level result

The next experiment expanded the edit vocabulary and changed the decision. A top-20 structural reranker improved zero-query selections from 284 to 323/576 on twelve fresh banks, all bank differences positive, and its later checkpoint scored 334. With the same 96 output calls, the later reranker scored 358 versus the old ranker's 321. Full source and target replay passed. The later-minus-earlier checkpoint gate failed because it won only seven banks; it remains in shadow. A task-level catalog choosing among rankers and first-query locations has 65 hindsight choices of headroom over the later reranker's frozen eight-call allocation, materially above the old whole-bank menus. See `CANDIDATE-EVALUATOR-GROWTH-RESULTS-2026-09-18.md` and `analysis/candidate-edit-catalog-headroom-v2-20260918.json`.
