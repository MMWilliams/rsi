# External output feedback on widened AST candidate pools

## Decision

**A bounded output-query sensor is a strong AST evaluator component at explicit oracle cost.** On twelve new eight-task banks with identical widened pools, the replay AST ranker selected **12/96** correct programs without a query. One top-20 entropy query per task raised selection to **36/96**; a second adaptive query raised it to **46/96**. Candidate reachability was **57/96**. One-query gain over no query was positive in all twelve banks, with an exact bank-resampling 95% interval of **+17 to +32 selections per 96**; the second query added ten, interval **+5 to +15**, at another 96 oracle outputs. The full reconstruction audit passed.

The study did **not** establish top-20 entropy as a superior query-selection policy. At the same one-query cost it scored **36/96** versus full-pool minimax **29** and deterministic random **31**, but top-20-minus-minimax gains occurred in five banks, with one loss and six ties. The declared seven-positive-bank gate failed, and its bank interval was **0 to +14**. At two queries, top-20 and weighted entropy tied at 46, top disagreement scored 45, minimax and random 42. Top-20's two-query advantage over minimax was +4 with interval −1 to +9. Treat the fixed policies as cost-aware controls, not a proven learned evaluator upgrade.

## Design and measured cost

Six mixed-stream seeds 902318–902323 generated full mixed banks before selecting eight AST tasks each; six AST-only seeds 902324–902329 generated eight AST tasks each. All tasks had one visible example, eight initially unlabeled probe inputs, and 15 final host-held examples. V67/V73 generated candidate pools at cap 512 per source. The evaluator predicted candidate outputs on the eight probe inputs, chose a probe using only those predictions and its frozen ranking, received exactly one oracle output, filtered matching candidates, and reranked. Two-query policies chose their second input after the first output using the same frozen algorithm. Every one-query method spent **96** oracle output calls; every two-query method spent **192**. The zero-query ranker bought none.

| Method | Oracle outputs | Correct / 96 |
| --- | ---: | ---: |
| Ranker alone | 0 | 12 |
| Random probe | 96 | 31 |
| Full-pool minimax | 96 | 29 |
| Top-20 entropy | 96 | **36** |
| Random sequential | 192 | 42 |
| Full-pool minimax sequential | 192 | 42 |
| Top disagreement sequential | 192 | 45 |
| Top-20 or weighted entropy sequential | 192 | **46** |

The mixed stream contributed 31 reachable tasks; top-20 one/two queries selected 19/25. The AST-only stream contributed 26 reachable; top-20 one/two selected 17/21. Preparation generated **48,296** candidate programs and **386,368** predicted candidate-output cells, requiring **67.2 seconds wall time** and **208.5 summed source-generation seconds**. Candidate execution for predicted outputs is local compute, distinct from the 96 or 192 exact oracle outputs. Source training costs for the ranker remain additional.

The runner froze seeds, tasks, pools, predicted outputs, rank scores, first probe choices, model and policy hashes before any target probe output or final label was opened. The second choice was allowed to depend on the first revealed output under the frozen policy. The audit regenerated all 96 tasks and candidate pools, recomputed all 386,368 predicted output cells and 96 rank/first-query records, and rechecked all 48,296 final candidate labels and resulting choices. It passed. Passing 15 final examples is a finite synthetic score, not proof of universal correctness.

## Implications for evaluator and improver growth

The sensor closes much of the **selection** gap once a correct program is in the pool: the two-query policy selected 46 of 57 reachable tasks. It also reveals a resource tradeoff. Query feedback improves the live evaluator's decision, but buying oracle outputs is not retained evaluator intelligence. The choice of top-20 entropy was researcher specified after development; its same-budget policy superiority failed the fresh bank gate. No improver learned to allocate, install, or inherit the sensor in this study.

The next step is a fixed **total query budget** test: an improver must decide which tasks get zero, one or two outputs using only public/predicted features and already verified feedback, versus one-per-task, fixed disagreement and random allocation at equal total calls. Separately test whether a later parent improver transfers that allocation/admission knowledge to a stronger child improver on new banks. Keep the fixed temperature map and no-query ranker as controls, and charge source acquisition cost.

Protocol: `EXPERIMENT-ast-probe-sensor-transfer.md`. Development: `analysis/ast-probe-sensor-development.json`. Runner and audit: `ast_probe_sensor_transfer.py`, `audit_ast_probe_sensor_transfer.py`. Frozen data: `runs/ast-probe-sensor-transfer-20260918/`.
