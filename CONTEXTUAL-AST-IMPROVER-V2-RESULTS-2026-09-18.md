# Contextual AST value estimation and child-improver transfer

## Decision

**No recursive improver growth is established.** On twelve untouched eight-task AST banks at exactly 96 true output calls per policy, the later ridge child's program choices scored **33/96**, compared with its earlier child at **31/96**, fixed one-query-per-task at **31/96**, and same-size scrambled/duplicated-history children at **30/96** each. The +2 child difference appeared in only **two of twelve banks**, with one losing bank and an exact bank-bootstrap 95% interval of **−2 to +7**. The prespecified child-growth gate failed. The later ridge **parent already scored 33/96** on these transfer pools; its new admission update changed six task allocations but added zero correct choices. The earlier ridge parent scored 30 and child 31. The observed later-child edge therefore cannot be credited to a positive feedback step that improved the later improver.

The nonlinear expanded-feature RBF child reached 32/96 versus its earlier child at 31, with just one positive bank and interval 0 to +3. Its admission gate rejected deployment, so the protected RBF policy used one query per task and scored 31/96. The ridge parent passed the protected admission rule by 21/48 versus fixed 19, with its two gains concentrated in one bank; its protected child scored 33/96. That gate prevents some weak updates but does not itself establish reliable transfer.

| Transfer policy, 96 calls | Correct / 96 |
| --- | ---: |
| Later ridge parent / child | 33 / **33** |
| Earlier ridge parent / child | 30 / 31 |
| Later RBF parent / child | 32 / 32 |
| Earlier RBF parent / child | 32 / 31 |
| Scrambled-history ridge child | 30 |
| Duplicated-history ridge child | 30 |
| Original ridge-100 child | 28 |
| Fixed one query per task | 31 |
| Fixed random, high entropy, high disagreement | 30, 27, 29 |

## What the development and fresh test say

On 288 inspected development tasks, 15 predefined linear/RBF settings underwent leave-one-bank-out comparison. Expanded RBF scored 113/288 against fixed one-each at 100; basic ridge-10 scored 109. On a separate **already inspected** 96-task panel, RBF scored 27 versus fixed 26 while basic ridge-10 scored 30. Both training rules were frozen for the new test. The fresh result favored the simpler ridge, but its +2 versus fixed one-each was concentrated in two winning banks with two losses; its paired interval versus fixed was **−4 to +9**. This is an observed score edge, not a promoted evaluator policy.

The newer source checkpoint used 384 historical verified task effects versus 288 for the earlier one. All children received the same 48 new admission task effects. Historical acquisition differs by 96 tasks, equivalent to 192 additional probe outputs plus final correctness labels and candidate work; equal transfer calls do not imply equal total compute. The admission/transfer run produced 144 new tasks, 70,532 candidate programs tested on final examples, and 564,256 candidate-predicted probe outputs. The independent reconstruction audit regenerated 20 source files, seven parent and seven child models, all task banks, pools, predictions, allocations, probe paths and final labels; it passed.

Transfer reachability was 54/96. The replay ranker solved 15/96 without a query, one query on every task solved 31, and two on every task solved 43 at double the call budget. A hindsight oracle with each task's true 0/1/2 outcome would score **43/96 at the same 96-call budget**; this is diagnostic headroom, not a deployable comparator. The ridge child's predicted first- and second-query gains correlated only 0.131 and 0.083 with realized gains. RBF's correlations were 0.285 and 0.066. The second-query value remains especially hard to predict before seeing the first output.

## Next experiment implied by the failure

The 0/1/2 allocator commits all eight calls before observing any output. A more direct feedback test should keep the same pool and total eight-call budget but allocate in **two stages**: buy a declared initial set of queries, update candidate sets from their actual outputs, then spend remaining calls according to the changed posterior and a learned value estimate. Compare a frozen adaptive rule, an incrementally updated adaptive rule, one-each, and the present ridge policy on fresh banks. Parent and child must each start from the same source checkpoint, receive equal new feedback and be evaluated on a second untouched bank. Report query placement, correctness, candidate reachability, posterior calibration and acquisition cost separately. This is still a researcher-defined edit type; self-generated improvements to the edit vocabulary remain untested.

Protocol: `EXPERIMENT-contextual-ast-improver-v2.md`. Development: `ast_value_feature_development.py` and `analysis/ast-value-feature-development.json`. Runner and auditor: `contextual_ast_improver_v2.py`, `audit_contextual_ast_improver_v2.py`. Frozen data: `runs/contextual-ast-improver-v2-20260918/`.
