# Seed search: evaluator growth and integration failure

Status: source search and first confirmation replay audits passed. The original seed-improver goal remains active. A second fresh experiment is in progress to test complete-policy integration and equal candidate-label budgets.

## What was compared

The source study compared five evaluator components (lexical, structural, behavioral, ensemble, guarded ensemble), five feedback tactics, three driving evaluators and three integration gates. Its 15 acquisition trajectories produced 75 checkpoints and 45 gate/configuration comparisons. It used 72 tasks with independently randomized visible examples.

The source rule selected an ensemble driven by uncertainty feedback with a retention gate: admission improved from 17/18 to 18/18 without a recorded regression. The initial lexical evaluator already scored 18/18 on this small source bank, so this result alone did not establish superiority over the strongest static component.

The first confirmation reset every arm to the same new bootstrap evaluator and feedback reservoir. It compared the five fixed tactics with empty, source-round-2, source-round-4, scrambled and online-updated controller knowledge. All arms purchased four task label sets per round for four rounds. Candidate-level label counts differed and are reported below. Final labels were opened only after all 50 checkpoint decisions were frozen.

## Evaluator improvement transferred

The preselected uncertainty strategy improved the ensemble's choices from 43 to 47 correct across the 48-task diagnostic total. Uniform feedback stayed at 43. Panels are distinct and should also be read separately:

| Confirmation panel | Tasks | Frozen ranker | Initial ensemble | Final uncertainty ensemble | Final deployed policy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mixed existing families | 24 | 20 | 21 | 23 | 21 |
| AST existing mechanisms, new visible examples | 12 | 6 | 10 | 12 | 8 |
| Four changed arithmetic mechanisms | 12 | 11 | 12 | 12 | 11 |

The pool contained a correct candidate for 47/48 tasks. Uncertainty, novelty and novelty/disagreement feedback reached that finite-example ceiling. This is positive evaluator-transfer evidence within the tested grammar, from one confirmation episode. The changed-mechanism panel was already 12/12 for the initial ensemble, so feedback did not improve that panel further.

## Feedback efficiency and inherited improver knowledge

| Feedback/controller | Evaluator curve, rounds 0–4 | Candidate oracle labels, including bootstrap |
| --- | --- | ---: |
| Uniform / empty knowledge | 43, 43, 43, 43, 43 | 206 |
| Uncertainty (source-selected) | 43, 43, 43, 43, 47 | 262 |
| Disagreement | 43, 43, 43, 43, 43 | 222 |
| Novelty | 43, 43, 47, 47, 47 | 256 |
| Novelty + disagreement | 43, 43, 47, 47, 47 | 256 |
| Source-round-2 controller | 43, 43, 43, 43, 43 | 236 |
| Source-round-4 controller | 43, 43, 43, 43, 43 | 236 |
| Scrambled effect controller | 43, 43, 43, 47, 47 | 250 |
| Inherited controller updated online | 43, 43, 43, 43, 43 | 220 |

Novelty and its combination were faster on the predeclared checkpoint metric, but their superiority over the preselected uncertainty tactic is an exploratory final comparison that needs replication. The learned contextual controller did not outperform empty knowledge and was outperformed by its single scrambled control. Its inherited effect table is not supported as a better improver. The simple source-selected static recipe is a stronger current candidate.

Equal task purchases did not produce equal candidate-label costs. In particular, uncertainty bought 262 labels versus uniform's 206. This is not a matched-oracle-execution gain. The next experiment imposes exactly 48 new candidate labels per round for every arm.

## The integration bottleneck

Despite the evaluator reaching 47/48, every arm's deployed policy stayed at 40/48. The integration code evaluated raw argmax choices on admission, then deployment added an extra 0.05 score margin over the frozen-base candidate. This uncalibrated margin blocked seven correct choices in the strongest final evaluator and rescued none in this episode. Four of the blocked choices were newly acquired feedback gains; three were already blocked initially.

The lesson is concrete: admission must evaluate the complete decision policy that deployment will execute. Scoring an evaluator and then changing its chooser rule is not a faithful integration test. The next candidate makes the model and chooser an indivisible proposed update.

Only one checkpoint update per arm was accepted in this confirmation. The strict accuracy gate saturated its small admission bank and rejected later ties. This is not evidence of compounding improvement. A fresh predeclared study will compare strict retention with a proper-score tie criterion while still measuring actual decision utility on sealed final cases.

## Representation and benchmark corrections

On the previously inspected AST diagnostic banks, the old lexical features collapsed correct and incorrect candidates together on 14/24 tasks. The new behavioral signature plus output-boundary structure had no such conflicts on those same banks. That is a development diagnosis, not a separate confirmation score.

The old source archive had 60 task IDs but only 46 distinct visible-example sets; 25 tasks belonged to repeated-visible groups. Both new studies generated public examples independently and checked visible-set uniqueness. The confirmation also excluded source visible sets. This reduces template replay as an explanation, while fixed grammar families and a small mechanism catalog remain important limits.

## Evidence and artifacts

- `runs/seed-source-search-20260917/`: replay audit passed, 144 candidate-source calls, 15 trajectories, 75 checkpoints.
- `runs/seed-confirmation-20260917/`: replay audit passed, 240 candidate-source calls, ten controller arms, five checkpoints each.
- `analysis/seed-confirmation-summary.json`: panel scores, learning curves, query counts, blocked decisions and accepted rounds.
- `output/seed-improver-candidate/state.json`: runnable source candidate, including evaluator state and transferable effect records. This is not a promoted optimal seed.
- `seed_candidate_cli.py`: public-example-only inference entry point.
- `SEED-INTEGRATION-NEXT.md`: corrections and requirements still open.

Both audits replay the same host interpreter. They establish deterministic reproduction and information-flow ordering under this local harness, not independent semantic correctness or protection from a malicious learner. The active goal still requires successful integration, stronger improver transfer, repeated useful updates, matched-budget evidence and independent replication.
