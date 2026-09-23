# Full mixed-system integration of the AST output sensor

## Decision

**A fixed AST output sensor passed the declared budgeted system-gain gate.** On six new 48-task mixed-mechanism banks, the prior zero-query fixed temperature map selected **140/288** correct programs. The same map with the replay AST ranker on widened AST pools selected **150/288** without a query. Adding one top-20 entropy output query to each of the eight AST tasks per bank selected **156/288**, using **48 oracle output calls** total. The sensor-system gain over the zero-query map was **+3,+3,+2,+3,+4,+1** by bank; all six improved and the exact six-bank resampling 95% interval was **+11 to +20 selections per 288**. The 288-task reconstruction audit passed.

This is a reliable **resource-bounded system improvement on the tested synthetic distribution**, not evidence that an improver learned to make the change. The zero-query ranker substitution contributed ten of the sixteen additional correct choices on this bank set, and the 48 output queries contributed six more. These effects must be kept separate. The replay AST ranker had failed an earlier full mixed promotion gate, so its zero-query gain here does not erase that instability.

## Same-budget policies

Every eight-call arm queried only AST tasks, held non-AST programs and the fixed temperature map constant, and used identical widened AST pools. One minimax query per AST task scored **157/288**, one top-20 entropy query **156**, and one deterministic random query **156**. The feedback-trained zero/one/two allocator scored **158**, versus a random zero/two allocator at **155**. Learned-minus-minimax bank differences were −1,0,0,+1,0,+1, interval **−2 to +4**. It failed the declared same-budget improver gate. Top-20 did not beat minimax either (−1,0,0,0,0,0).

| System policy | Oracle outputs | Correct / 288 |
| --- | ---: | ---: |
| Prior fixed temperature map | 0 | 140 |
| Fixed map + AST ranker, no query | 0 | 150 |
| Fixed map + random AST probe | 48 | 156 |
| Fixed map + top-20 entropy AST probe | 48 | 156 |
| Fixed map + minimax AST probe | 48 | 157 |
| Fixed map + learned AST allocation | 48 | **158** |
| Fixed map + two top-20 AST probes each | 96 | 162 |

AST candidate reachability rose from **11/48** under the old cap to **26/48** under V67/V73 cap 512; total reachability rose **237→252/288**. Of those 26 reachable AST tasks, the AST ranker selected ten without a query, the one-query fixed methods selected 16–17, the learned allocation selected 18, and two queries each selected 22. The five non-AST mechanisms made exactly the same choices across all arms.

## Evidence and limits

Seeds 902342–902347 were fixed before final labels. The runner saved all 288 tasks, baseline and widened pools, 196,016 candidate-predicted outputs, model hashes, rank scores, first probes and eight-call allocations before revealing any true probe outputs or final labels. Preparation generated **52,128** baseline candidate entries and **24,502** entries in the separately saved wide AST pools; wall time was **151.1 seconds**, with **703.8 summed source-generation seconds** across workers. The audit regenerated tasks and pools, recomputed all 196,016 predicted output cells, six allocations and **76,630 distinct stored-pool candidate labels**, and matched every final outcome. It passed.

The 48 and 96 query figures are logical oracle-call costs for one deployed arm. The offline scorer read sealed outputs to evaluate counterfactual arms, so wall time is not a measured live serving cost. Candidate generation, candidate-predicted outputs, prior ranker training labels, and allocator source feedback are additional resource costs. The simulator's host family tag still routes candidate sources; the evaluator uses public Unicode block to route its AST branch. The task rules are a narrow synthetic benchmark and final correctness is measured on 15 hidden examples.

## Seed-improver implication

The strongest **supported budgeted component** is the fixed map plus one output query per AST task; the particular one-query probe selector has not shown reliable superiority over other fixed selectors. The learned allocator's observed 158 is the highest score in this run at 48 calls, but its one-task edge over minimax is uncertain and does not justify promotion. The zero-query fixed map remains the control when output calls are unavailable.

The next improver experiment should give parent checkpoints the same edit catalog (cap, ranker, one-query sensor, query allocation and rollback), a protected admission bank and equal acquisition/query budgets. Apply their resulting **child improvers** to the same frozen base on another untouched bank. Require a later parent to produce a stronger child than the initial parent, scrambled inherited state, and the strongest fixed budgeted schedule. That recursive test has not yet passed.

Protocol: `EXPERIMENT-full-mixed-ast-sensor.md`. Runner and audit: `full_mixed_ast_sensor.py`, `audit_full_mixed_ast_sensor.py`. Frozen data: `runs/full-mixed-ast-sensor-20260918/`.
