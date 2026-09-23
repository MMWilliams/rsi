# Prospective candidate-evaluator feedback transfer

Frozen on 2026-09-18 before generating seeds 902510–902521.

## Question

Can verified candidate-level feedback make a later evaluator checkpoint rank better programs on fixed candidate pools, and does that evaluator edit remain useful when integrated with the existing eight-call sensor allocation? This tests evaluator growth and a fixed integration. It does **not** establish that an improver invented the edit or can produce a better child improver.

## Fixed source and checkpoints

- Use the audited full-width AST/public-block ranker candidate pools from the previous cross-family meta run. For each source task, label up to the old ranker's top 20 candidates by the exact external interpreter on the final 15 hidden examples.
- Public features per candidate: 175 structural features from the visible task and program, old-ranker score gap and rank, pool size, and six public mechanism indicators. Hidden outputs and correctness are target labels only.
- E0: histogram gradient boosting classifier with 15 leaves, minimum leaf 80, learning rate .05, 100 iterations, L2 1, seed 0, trained on the 576 tasks in meta admission+A.
- E1: same algorithm and settings with 288 additional verified meta-B tasks (864 source tasks total).
- Capacity control: 7-leaf model on the same 864 tasks. Scrambled control: 15-leaf model on the same 864 tasks with candidate correctness labels rotated within each task, preserving each task's positive count. Old frozen ranker is the no-edit control.

Freeze model files, source hashes, protocol and runner before new task generation. Both E0 and E1 score only the old top 20, then place those 20 first in their order while leaving the remaining pool in the old order. Thus candidate generation and full pool reachability are identical across policies. Each task's top choice is frozen before final labels are opened.

## Fresh evaluation

Generate twelve independent 48-task mixed banks, one visible and 23 hidden examples per task. Use the same six-mechanism generator, full-width AST candidate branch, public-block temperature route and replay AST ranker. Save all tasks, pools, original scores/orders, top-20 structural features, model scores/orders, predicted outputs, sensor probe indices and budget choices before scoring hidden labels.

Primary endpoint: E1 minus E0 **zero-query** correct top choices on the same pools. Report paired bank differences and exact bank-bootstrap interval. Promotion requires at least +8 correct choices, at least eight positive banks, no more than two losing banks, a positive lower interval endpoint, E1 ahead of scrambled and 7-leaf controls, and no harm on the eight-call integration endpoint relative to E0. Compare both checkpoints with the old ranker and report top-20 and full-pool reachability separately.

Secondary integration: use the earlier frozen E0 task-level query allocator to buy eight exact outputs per bank. The allocation and top-20-entropy probe index are the **same** for every ranker policy. The observed output filters the full candidate pool; each policy takes its first surviving program. This isolates the ranker edit under a common sensor budget. Report final correctness, selected marginal gain, prediction cells and true output calls. Also report no-query and one-call-per-task references as separate budgets.

Acquisition and inference accounting includes source candidate labels, structural extraction, model fitting, fresh candidate generation, top-20 rescoring, predicted output cells and exact output calls. The external oracle and held-out labels are outside evaluator write access. Independently regenerate source training examples, fresh tasks/pools/features/predictions, allocations and final labels.
