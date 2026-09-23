# Incremental verified-feedback replay for AST evaluation

## Decision

**The replay-updated AST evaluator passed its declared fresh transfer gate as a scoped evaluator checkpoint.** After incorporating verified candidate outcomes from two inspected AST transfer streams, the new checkpoint selected **13/96** correct programs on twelve new eight-task banks, versus **7/96** for its previous checkpoint and **0/96** for the original temperature-0.25 parent. All three saw the same **47,546** candidate programs and used zero inference oracle output queries. Reachability was **49/96**.

The updated-minus-previous bank differences were **+1,0,0,+1,+1,0** in the mixed stream and **+1,+2,0,0,0,0** in the AST-only stream. Five banks improved, seven tied, none regressed. The exact 12-bank resampling 95% interval for the total gain was **+2 to +11 selections per 96**; stream-stratified resampling gave the same interval. Each stream gained three correct choices. The complete 96-task reconstruction audit passed. This supports a narrow retained evaluator improvement across new instances of the same two synthetic AST rules. It does not prove a better improver or broad intelligence growth.

## Feedback and controls

The prior specialist had been trained on 23,686 verified labels from 48 inspected AST tasks. It scored 6/48 on one fresh AST-only stream, then 0/48 on a second fresh mixed stream, so its first positive result was not robust. Those two transfer sets were then treated as **inspected source feedback**, never as confirmation for this update. The new edit began at the first specialist's weights and trained 40 more listwise epochs at learning rate 0.0001 on **48,596** verified candidate labels from the two 48-task streams, with the old normalization and architecture fixed. Source fit rose from 6/96 to 18/96 among 52 reachable tasks. The fresh test was required to determine whether that translated.

New mixed-stream seeds 902300–902305 generated full 48-task mixed banks before selecting eight AST tasks per bank. Separate AST-only seeds 902306–902311 generated eight AST tasks each. This preserves both prior generation modes. V67/V73 generated cap-512 candidate pools from one public example; the last 15 host-held examples scored final correctness. All tasks, pools, model hashes and choices were saved before target labels were opened.

| Fresh stream | Reachable | Parent 0.25 | First specialist | Replay update |
| --- | ---: | ---: | ---: | ---: |
| AST-only, 48 tasks | 29 | 0 | 4 | **7** |
| Mixed-stream AST, 48 tasks | 20 | 0 | 3 | **6** |
| **Combined, 96 tasks** | **49** | **0** | **7** | **13** |

The audit regenerated all 96 tasks and pools, recomputed all three choices per task and rechecked all 47,546 candidate outcomes. It passed. Preparation took **71.9 seconds wall time**, with **231.4 summed source-generation seconds** across workers. The new training pass itself took 1.2 seconds after feature extraction. Total acquisition for the current checkpoint includes the parent's earlier 31,500 labels, the first specialist's 23,686 labels, and this update's 48,596 labels; its inference comparison alone is pool- and query-matched, not total training-cost-matched.

## Integration implications

The current best-supported **AST specialist checkpoint** is this replay update, but it selects only 13 of 49 reachable programs. Keep the general evaluator and prior fixed temperature map for other mechanisms. A public-context gate with the first specialist failed on a prior fresh mixed test; the new specialist still needs a full fresh mixed-bank integration and retained non-AST check before becoming a system component.

The causal distinction remains: a researcher specified the cap, feedback replay, loss and route. Verified feedback improved an evaluator checkpoint, but an improver has not yet learned to select this edit, reject the failed first specialist, preserve other capabilities, or produce a better child improver. The next parent/child experiment must compare those abilities against fixed edit schedules at the same feedback and candidate budget. A development screen of semantic candidate-consensus edits failed on both inspected streams (`analysis/ast-candidate-consensus-development.json`) and is not promoted.

Protocol: `EXPERIMENT-ast-feedback-replay-update.md`. Model: `analysis/ast-feedback-replay-model.json`. Runner and audit: `ast_feedback_replay_update.py`, `audit_ast_feedback_replay_update.py`. Frozen data: `runs/ast-feedback-replay-transfer-20260917/`.
