# RSI prototype: completed pilot and verdict

The prototype runs locally on the second RTX 5090. The tested system includes bounded DSL search, progressive widening, syntactic transpositions, verified macros, operator-effect memory, table inheritance controls, local model-generated edit expressions, independent execution sensors, deterministic replay, and a coupled Qwen/LoRA search-and-distill loop.

**Verdict: RSI was not demonstrated. The test exposes the difference between improved low-k answers and durable coverage, and between a tuned searcher and an improved improver.**

The controlled result is [`pilot-20260916-v2-complete`](runs/pilot-20260916-v2-complete/REPORT.md). Its full [measurements](runs/pilot-20260916-v2-complete/results.json), [independent audit](runs/pilot-20260916-v2-complete/audit.json), and [pass@k chart](runs/pilot-20260916-v2-complete/pass-at-k.png) are saved. The [run history](RUN-HISTORY.md) records earlier diagnostic and interrupted runs.

## Raw model coverage

Qwen3-0.6B; one neural training seed; 24 fresh final tasks; 64 independent samples per task. All three arms start from identical LoRA tensors after 32 shared bootstrap steps on 46 oracle-verified search trajectories. Subsequent training uses disjoint tasks and 48 optimizer steps per round for each arm.

| Checkpoint | pass@1 | pass@8 | pass@64 | Tasks reached at 64 samples |
| --- | ---: | ---: | ---: | ---: |
| Shared initial model | 5.1% | 11.2% | 29.2% | 7/24 |
| Adaptive search + distillation, round 1 | 19.0% | 25.9% | 33.3% | 8/24 |
| Adaptive search + distillation, round 2 | 17.7% | 20.8% | 20.8% | 5/24 |
| Fixed search + distillation, round 2 | 18.4% | 20.8% | 20.8% | 5/24 |
| Verified self-training, round 2 | 5.7% | 12.6% | 16.7% | 4/24 |

The first distillation increases measured large-k coverage by one task, but the second loses that gain and falls below the initial model. The adaptive and fixed amplifiers finish at the same pass@64. This fails the proposed coverage-compounding criterion. Higher pass@1 alone would have concealed the regression.

The current distillation schedule trains on each round's newly verified solutions rather than a balanced cumulative replay set. Forgotten earlier skills and concentration on a small target set are plausible explanations, not established causes. A follow-up should test cumulative verified replay, regularization toward the parent checkpoint, and a separate validation gate on model updates. Those changes must use fresh final tasks; do not tune on this final bank.

## Artifacts and improvers

On the 64-task search final bank, mean selected-answer accuracy across three edit seeds rises from **70.3% to 71.4%** by generation 6. Random edits through the same gates also finish at **71.4%**. Learned edit selection has not earned an advantage over that control.

For the inheritance test, every condition restarts from identical code, search configuration, operator catalog, and macro library. Each restart gets six generations with four edit proposals per generation. Results below average six paired restarts on a separate 64-task transfer bank.

| Inherited effect table | Mean final accuracy |
| --- | ---: |
| Generation 0 / empty | 75.0% |
| Generation 3 | 75.5% |
| Generation 6, intact | 75.3% |
| Generation 6, scrambled | 75.8% |

Generation 6 minus empty is **+0.26 percentage points**, with a descriptive paired-restart bootstrap interval of **[-1.04, +1.56] points**. Generation 6 minus scrambled is **-0.52 points**, interval **[-2.08, +1.04]**. Restarts share source tables and tasks, so these are not confidence intervals over independent research replications. They provide no basis for claiming better inherited improvement ability.

## New edit operators

Two unique model proposals passed structural parsing. One failed its parameter bounds; one passed replay, sensors, development improvement, and admission non-regression. With the admitted operator available, a later matched-budget catalog comparison solved one extra transfer task in one of three seeds and tied in the other two: **+0.52 points on average**. That is weak pilot evidence for this particular expression. The operator is a new bounded combination of search-setting edits, not an unrestricted new algorithm or a demonstration of level-3 RSI.

## Integrity and reproducibility

- **23 regression/integrity tests pass**, including independent semantics, negative-zero handling, forged-score rejection, hidden-data exclusion, journal corruption detection, pass@k arithmetic, adapter isolation, common precision, and unique operator identity.
- **7,680 saved raw samples** were regraded with the published interpreter and reconciled against the reported metrics.
- **179 saved training trajectories** were independently rechecked, including the common bootstrap and all three arms.
- **1,862 evaluation batches were replayed** across the reused CPU stage and continuation, with **zero experimental sensor incidents**.
- Every run preserves configuration, task hashes, source snapshots, event journal, raw generations, trajectories, and saved LoRA adapters. The CPU stage was reused only after its source/config/bank hashes and journal chain matched.

The protected boundary is the bounded proposal interface and trusted host, not an OS sandbox for arbitrary native code. Verification is exact on the tested strings, not a proof of equivalence on every possible input. Primitive/oracle counters are charged logical work estimates; they are not FLOPs, and some duplicate self-training candidates avoid repeated physical verification. Measured neural generation time was about **374 seconds**, and training time about **60 seconds**, excluding the separately recorded CPU stages. Total compute differs across neural arms, despite matched optimizer steps.

## Next changes justified by the result

1. Add a model-promotion gate that measures validation coverage before retaining a new LoRA update. Search edits already have gates; the distillation stage also needs an explicit rollback criterion.
2. Compare cumulative verified replay and parent-policy regularization against the current fresh-round-only distillation. Keep both low-k and large-k coverage as primary outcomes.
3. Replace the global average per-operator table with estimates conditioned on the parent configuration and task features. The current table does not transfer more useful selection knowledge than its controls.
4. Run the improved protocol with multiple neural seeds and matched total compute. Only then test a larger model or broader programming domain.

This pilot supplies working machinery and a falsifiable negative result. It does not justify calling the current system optimal or claiming that recursive self-improvement has been achieved.
