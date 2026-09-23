# Full-system test of the replay-updated AST evaluator

## Decision

**The replay-updated AST specialist remains an unpromoted component.** On six new 48-task mixed-mechanism banks, combining it with the prior fixed block-temperature map scored **155/288** versus **152/288** for the fixed map on identical pools. The gain occurred in only two of six banks: **+1,0,0,+2,0,0**. Its exact six-bank resampling 95% interval was **0 to +7 selections per 288**, so the declared integration gate failed. The replay specialist and the first specialist each selected **3/48** correct AST programs here; their paired bank difference was +1,0,−1,0,0,0, interval −3 to +3. The reconstruction audit passed.

This tempers the preceding 96-task AST-only/mixed-stream evaluator result: that checkpoint did show a positive same-pool improvement over its predecessor on those fresh instances, but its advantage did not repeat in this full six-mechanism stream. It cannot yet be called the best seed improver, and no parent-to-child improver-growth result exists.

## Paired outcomes

Each bank had eight tasks from each of six synthetic mechanisms. The AST source cap was raised from 128 to 512 for V67/V73 only. Total reachability rose from **240/288 to 250/288**; paired bank gains were +5,+1,+1,+2,0,+1, with an exact resampling interval of **+4 to +19**. AST reachability was **13/48** at cap 128 and **23/48** at cap 512. The wider generator found programs the old pool missed, but the replay specialist selected only three of those 23 reachable tasks.

| Policy | Correct / 288 |
| --- | ---: |
| Parent temperature 0.25, cap-128 pools | 148 |
| Parent temperature 0.25, widened AST pools | 148 |
| Replay specialist used globally | 122 |
| Parent plus first AST specialist gate | 151 |
| Parent plus replay AST specialist gate | 151 |
| Prior fixed block-temperature map | 152 |
| Fixed map plus replay AST specialist | **155** |

The public gate used Unicode input block 0x800 to select the specialist and otherwise retained the parent or fixed map. This avoided global retention losses by construction. Global use of the new specialist fell to 122/288, with the largest losses on self-edit (43→26) and transformation (15→8) compared with parent 0.25. The map itself was fixed from earlier inspected development evidence. The simulator's family tag still selected candidate source pairs, as in previous studies; it was not a feature for evaluator choices. These synthetic block cues are not a demonstrated general mechanism detector.

The runner froze seeds 902312–902317, all tasks, candidate pools, model hashes and choices before final labels. Preparation generated **51,112** cap-128 candidate entries and **23,670** entries in the separately saved wide AST pools; wall time was **171.9 seconds** and summed source-generation time was **815.7 seconds** across workers. Inference bought zero oracle output queries. The replay specialist had already consumed 48,596 extra source candidate labels on top of the first specialist's 23,686 and the parent's original 31,500. The audit regenerated all 288 tasks and pools, recomputed 576 base/wide choice sets and rechecked **118,892** candidate outcomes. It passed.

## What this changes

The present best supported **zero-query whole-system control** is the prior fixed temperature map, not the replay specialist gate. The specialist is a viable edit type for future admission tests but has not passed full integration. The current bottleneck is choosing among correct AST candidates that the wider generator does reach. An external output-query sensor is likely a stronger immediate AST evaluator component, but it must be compared at a declared query and total acquisition budget; earlier learned query-allocation policies failed their strongest fixed controls.

For improver growth, the next decisive test is not another global replacement. Give initial and later parent improvers the same bounded catalog, verified feedback, public context and cost limit. Require them to reject harmful global installs, decide when a specialist or query sensor helps, preserve the fixed-map baseline, and then compare the resulting **child improvers** on an identical starting system and second untouched bank. Current edit choices and routes were researcher specified, so this recursive endpoint remains open.

Protocol: `EXPERIMENT-gated-ast-replay-integration.md`. Runner and audit: `gated_ast_replay_integration.py`, `audit_gated_ast_replay_integration.py`. Frozen data: `runs/gated-ast-replay-integration-20260917/`.
