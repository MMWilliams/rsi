# Listwise evaluator plus budgeted external sensor: frozen test

Date: 2026-09-18. Written before generating or scoring target banks.

## Question

Does verified feedback improve the policy that chooses which tasks receive one exact output check after task-level listwise ranking? Do the learned selector and the listwise ranker integrate better than a fixed entropy allocator at the same four-output-call-per-eight-task budget? This is an evaluator and sensor integration test. It does not by itself prove an improving improver.

## Source and target

The frozen listwise top-200 model and two specialist models are unchanged. Early task-query-value selectors train on 192 opened source task effects, with one verified output and external hidden-example labels per task. Later selectors add 384 opened task effects from a disjoint audited replication panel (576 source task effects total). Use the same 27 public features of visible example, pool/ranker confidence and predicted probe partitions. Compare a regularized class-balanced logistic model and the specified depth-2 histogram gradient booster. Scrambled-added-effect and duplicated-early-history controls use the same added-row count as later. Source acquisitions and positive effects are reported separately.

Target: 24 new deterministic eight-task familiar/shifted AST banks, seeds 905700–905723 (192 tasks). Generate the common verified candidate pools and public predicted probe outputs. The host may hold sealed hidden examples, but task selection receives no true probe outputs, hidden suffix, family or reference. Ranker scores, probe location, public feature vectors, model forecasts, four selected IDs per bank and file hashes must be frozen before any target true output or hidden correctness label is read. Each selective arm is charged exactly one external output for each of its selected tasks. After all arms are frozen, the measurement host opens all 192 task outputs to score every arm, all-query and hindsight ceilings; report those 192 measurement-oracle accesses separately from the 96 deployment calls per selective arm. Every arm uses the same listwise top-200 ranker and candidate pool.

## Arms, budget and gates

At exactly four output calls per bank (96 total): early/later logistic, early/later HGB, scrambled-HGB, duplicate-HGB, fixed predicted-probe entropy, fixed low ranker margin, fixed ranker disagreement and seeded random. No-query, query-every-task and retrospective oracle-four are cost/headroom anchors. Freeze all arm allocations before scoring. Charge exact candidate-score and predicted-output-cell counts, source effect acquisition, 96 live outputs, model prediction passes and preparation wall time separately.

The *sensor integration gate* requires later logistic to exceed no-query by at least six correct tasks, with a positive paired 95% bank-bootstrap lower bound and at least eight positive banks. The *incremental selector gate* requires later logistic to beat early logistic, scrambled-HGB and duplicate-HGB by at least four tasks each, with a positive lower bound and at least eight positive banks against early. The *fixed-policy gate* requires later logistic to beat fixed entropy, low margin and random by at least four tasks each, with a positive lower bound and at least eight positive banks against fixed entropy. Audit must pass. Report all contrasts, including failures and harmful queries. No model or threshold tuning on target outcomes.

Replay target generation, public features, all allocations, actual query outputs, post-query choices, all exact candidate labels and source model hashes. Correctness on finite hidden examples does not prove universal program correctness; this is a synthetic AST contract, not transfer to research, cybersecurity, social good or policy tasks.
