# Incremental AST evaluator and improver checkpoint transfer

Frozen before admission and transfer labels on 2026-09-18. This is a scoped test of **feedback-trained query allocation**, not open-ended RSI. Candidate generator, AST ranker, probe selector, feature vocabulary, ridge training rule, and 0/1/2 query action space are fixed. A later checkpoint changes only the learned query-value table. A child improver is that same rule after a common new batch of verified feedback.

## Source and controls

I0 uses 96 inspected AST sensor tasks (the original allocation training set). I1 uses those 96 plus 96 inspected allocation-transfer tasks and 48 inspected AST tasks from the full mixed-system trial, for 240 source tasks. The latter 144 task effects were inspected before this protocol; their acquisition cost is **additional**, not matched to I0. A scrambled control has the same 240 feature rows and marginal-effect pairs as I1, but rolls the 144 added effect pairs by one within each source stream. A duplicate control adds 144 repeated I0 rows instead of new information. Ridge penalty remains 100; no parameter search on admission or transfer.

All arms see the same V67/V73 cap-512 candidate pools, replay AST ranker, public features, top-20 entropy query selection, and exact eight-call knapsack per eight-task bank. Fixed controls are one call per task and the previously defined random, entropy, and disagreement two-on-four allocations.

## Protected sequence

1. Save source hashes, all parent weights, and source/control row identities. Generate six fresh eight-task admission banks: mixed seeds 902348–902350 (generate full 48-task banks before selecting AST), AST-only seeds 902351–902353. Freeze each parent's eight-call allocation using only public examples, candidate scores and candidate-predicted probe outputs.
2. Reveal two true probe outputs per admission task (96 calls total), plus held-out final correctness from the external oracle. Reconstruct each task's 0/1/2-call outcome. Train each child from its own original source table plus the **same** 48 admission effect rows. This is equal new feedback for every child, but unequal cumulative source acquisition.
3. Generate twelve untouched eight-task transfer banks: mixed seeds 902354–902359 and AST-only seeds 902360–902365. Freeze each child allocation and all fixed controls before opening true probe outputs or final correctness. Score 96 total logical query calls per deployed policy over 96 tasks.

Primary recursive endpoint: I1 child minus I0 child correct program choices on the 12 transfer banks. Require at least eight positive paired banks, exact bank-resampling 95% interval lower bound above zero, and I1 child at least the strongest fixed control. Also report parent improvement on admission, child versus its own parent on transfer, child versus scrambled and duplicate controls, reachability, acquisition/inference costs, and per-bank differences. A better child would be **bounded improver improvement** in this fixed edit space; broader intelligence growth requires more mechanisms, richer edit types and replication. If the gate fails, retain the fixed one-query policy.

The scorer can inspect all counterfactual 0/1/2 outcomes for analysis. A deployed policy only receives the outputs it purchases. Acquisition calls, candidate labels, candidate-output predictions and preparation time must be reported separately. An independent audit must regenerate tasks/pools/predictions and reconstruct allocations and outcomes.
