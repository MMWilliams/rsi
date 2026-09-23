# Cross-component evaluator edits on a common mixed bank

## Decision

**Keep the public-context temperature map and the fixed AST output sensor. Do not apply the sharper listwise loss globally.** On six untouched 48-task banks, the fixed map scored **145/288** without output calls. Global temperature 0.25 scored **139/288** on the same pools and no-call budget; its paired bank differences were −1,0,−3,−1,0,−1, with an exact bank-bootstrap 95% interval **−11 to −2**. The losses were four transformation and two self-edit tasks. The earlier three-family result in favor of temperature 0.25 remains valid in its scope; the common six-mechanism test shows why a public-context route is necessary.

The fixed map plus the widened AST replay ranker scored **148/288** without a query. One top-20 entropy output query on each AST task raised this to **159/288** at **48 calls**: six positive bank gains versus the no-query fixed map, interval **+10 to +19**. This independently repeats the earlier budgeted mixed-system gain (140 to 156/288 at 48 calls). The output-query contribution beyond the AST ranker was +11 tasks here, with five winning banks and one tie, interval **+6 to +16**. Widening the AST pool raised AST reachability from **9 to 23/48**; reachability is kept separate from evaluator selection.

The shadow sequential AST allocator reached **161/288** at the same 48 calls, versus top-20 one-each at 159 and minimax one-each at 158. Its +2 over top-20 appeared in only two banks, interval **0 to +4**; over minimax its interval was **−2 to +8**. Its earlier protected admission gate had already rejected deployment, and the fresh result does not satisfy the declared five-bank promotion rule. It remains a research arm.

| Policy on the same 288 tasks | Output calls | Correct |
| --- | ---: | ---: |
| Fixed public-context temperature map | 0 | 145 |
| Global temperature 0.25 | 0 | 139 |
| Fixed map + AST replay ranker | 0 | 148 |
| Global sharp + AST ranker | 0 | 142 |
| Fixed map + AST top-20 query each | 48 | 159 |
| Global sharp + AST top-20 query each | 48 | 153 |
| Fixed map + AST minimax query each | 48 | 158 |
| Fixed map + sequential AST allocation | 48 | **161** (shadow) |
| Global sharp + sequential AST allocation | 48 | 155 |

## Edit-effect diagnosis

The two inspected full-mixed panels now contain balanced task-level outcomes for 576 tasks. Changing the fixed map to global temperature 0.25 produced **six task wins and fifteen losses**: three wins and ten losses in transformation, three wins and five losses in self-edit. The sensor edit (one top-20 query versus AST ranker without a query) produced **seventeen AST task wins and no losses** on those panels. A global scalar edit-effect table is therefore unlikely to improve this catalog much: the strong sensor is already a fixed choice, and the sharp edit is harmful on average outside its supported context.

The larger missed opportunity is elsewhere. In the fresh panel, transformation and mutation candidate pools were each reachable on **48/48** tasks, but the fixed map selected only **21/48** and **23/48** respectively. Stack was reachable 48/48 and selected 37. These are evaluator misses in available pools. Before searching more AST-only allocation rules, test whether external output queries and feedback-trained selection on these non-AST families recover correct candidates under the same *total* 48-call budget. This creates meaningful cross-family edit choices for a later improver. Candidate reachability, query value, and final correctness must be attributed separately.

## Verification and limits

All six fresh banks and both cap-128 base pools and cap-512 AST pools were frozen before true outputs or final labels. The full reconstruction audit regenerated **288 tasks**, **51,510 base candidate entries**, **25,032 wide AST entries**, **200,256 candidate-predicted AST outputs**, all ranker decisions, **76,542 candidate final-label checks**, and all **48 sequential AST query actions**. It passed. Each 48-call policy used exactly eight calls per bank; the scorer's counterfactual reads and source-training labels are extra research costs, not free deployed calls. The benchmark is synthetic and final correctness is agreement on fifteen held-out examples, not universal equivalence.

Protocol: `EXPERIMENT-cross-component-mixed-transfer.md`. Inspected development matrix: `analysis/cross-component-catalog-development.json`. Runner and auditor: `cross_component_mixed_transfer.py`, `audit_cross_component_mixed_transfer.py`. Frozen run: `runs/cross-component-mixed-transfer-20260918/`.
