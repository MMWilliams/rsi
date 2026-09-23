# Incumbent-aware evaluator-rule selection: fresh transfer

## Decision

**Do not promote the incumbent-aware tie correction as an improving improver.** On twelve untouched 48-task mixed banks, the corrected later child, original catalog later child and initial child each selected **349/576** correct programs with 96 true output calls. The corrected child scored below its own frozen parent (**350**) and a duplicated-history child (**353**). It beat the initial child on only two of twelve paired banks; the exact bank-bootstrap 95% interval for its total difference was **-4 to +4**. The prespecified recursive gate and the secondary tie-correction gate both failed.

| Policy on the same 576 tasks | Correct | True output calls |
| --- | ---: | ---: |
| No query | 304 | 0 |
| Strongest fixed schedule, transformation only | 341 | 96 |
| Initial child | 349 | 96 |
| Original catalog later child | 349 | 96 |
| **Incumbent-aware later child** | **349** | **96** |
| Later frozen parent | 350 | 96 |
| Scrambled-history child | 350 | 96 |
| Duplicated-history child | 353 | 96 |
| Fixed ridge-10 on later child's rows | 349 | 96 |
| Fixed ridge-100 on later child's rows | 349 | 96 |

Panel A favored the catalog later child by one (183 versus 182). Panel B favored the incumbent-aware child by one (167 versus 166). The correction therefore tied overall. Its paired-bank interval versus the catalog child was also **-4 to +4**. Candidate reachability was **492/576**; the query policies remain well below the available-pool ceiling, but this experiment does not identify a better rule selector.

The incumbent-aware policy's eight-choice edge over the strongest fixed query schedule had seven positive banks and a **0 to +17** paired-bank interval. That comparison is descriptive here; it does not independently pass a strictly positive interval gate. The earlier cross-family allocator study provides the stronger scoped evidence for feedback-trained query allocation.

## What was tested

The previous training-rule experiment showed a validation tie: after the common admission update, interaction ridge-10 and ridge-100 each scored 704/1,152 in the later child's source cross-validation. A frozen catalog-order tie-break selected ridge-100, which did worse than fixed ridge-10 on that experiment's transfer banks. We treated those opened banks as development data and froze one correction before opening this study's seeds: **retain the parent's incumbent rule on an exact validation tie**. The later parent had ridge-10, so its corrected child used ridge-10; the initial parent's ridge-100 switched to ridge-10 because the new source evidence favored ridge-10 by five. All other models, candidate pools, public features, rankers, probes and call budgets were held fixed.

The corrected child is *identical by construction* to fixed ridge-10 fitted on the later child's 1,152 rows; its tie against that control is not evidence of an adaptive advantage. Both ridge penalties tied at 349 on these fresh tasks, explaining why the tie correction itself produced no net improvement. The duplicate-history control scored highest among these learned states, a warning that apparent gains from inherited rows can depend on weighting rather than useful new information. This is a diagnostic observation, not proof that duplication is a generally superior improver.

The initial lineage inherited 576 older task effects; the later lineage inherited 864. Both had already received the same 288 admission effects in the prior study, yielding 864 and 1,152 training rows respectively. Those source and admission labels and probe outputs are **additional acquisition costs** outside the 96 matched new transfer calls. This test uses the same six synthetic string-program mechanisms and a visible Unicode-block mechanism cue. It does not test novel edit types, new domains, model-weight growth, or general recursive self-improvement.

## Verification and next action

Both new panels' tasks, pools, predicted probe outputs, ranks, features and policy call allocations were frozen before either panel was scored. The runner evaluated **133,568 candidate final labels** and **1,068,544 candidate-predicted probe-output cells**; preparation took **275.4 seconds wall time** across panels. The **independent audit passed**: it reconstructed the states and all 576 fresh tasks, candidate pools, predictions, ranks, features, 192 bank-policy allocations, all 133,568 final candidate labels and their bank-policy scores. Its record is `runs/stable-cross-family-improver-transfer-20260918/audit.json`.

The earlier transferable **evaluator** gain remains evidence for a scoped query-allocation component. Two fresh improver tests now fail to show that more inherited query effects or a more careful rule tie-break produces a better child. The next decisive experiment should offer the improver edit choices that change distinct bottlenecks—candidate reachability, evaluator ranking, output-sensor use and rollback—on a common base, with balanced effect trials and disjoint child-transfer banks. Use the present transfer outcomes only as development evidence for design, never as the next final holdout.

Protocol: `EXPERIMENT-stable-cross-family-improver-transfer.md`. Runner: `stable_cross_family_improver_transfer.py`. Auditor: `audit_stable_cross_family_improver_transfer.py`. Frozen run: `runs/stable-cross-family-improver-transfer-20260918/`.
