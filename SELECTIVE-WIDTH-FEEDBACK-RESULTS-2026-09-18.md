# Incremental width-feedback test

The fresh test **did not demonstrate improver intelligence growth**. A better scoped solver result came from widening selected candidate shortlists, but 192 additional verified edit outcomes did not make the later width selector better than its earlier checkpoint or a fixed public rule.

## Design and audit

The [frozen protocol](EXPERIMENT-selective-width-feedback-transfer.md) used 24 new mixed familiar/shifted AST banks (192 tasks), a common generator, old-ranker order, and the two already validated specialist rankers. Every task received top-100 scoring. Each selective policy could additionally score candidates 101–200 for four tasks per bank. Choices were frozen from public task features and model predictions before external hidden-example labels were read. The early two-head edit selector trained on 384 previously opened task effects; the later one added 192. Scrambled and duplicate-history controls had 576 training rows each. The exact interpreter remained outside the selector.

The [audit](runs/selective-width-feedback-transfer-20260918/audit.json) passed after replaying all 192 tasks, 756,912 candidate-output prediction cells, 1,536 target selector-model predictions, frozen selections, and 94,614 candidate labels. The run's first score attempt stopped before opening labels on a JSON list/tuple manifest mismatch. Two serialization-only corrections were made to manifest and audit comparisons; script hashes and the results manifest link were updated. Frozen task, pool, model and selection hashes, and scored outcomes, were unchanged.

## Fresh results

| Policy | Correct / 192 | Extra specialist candidate scores | Beneficial edits selected |
| --- | ---: | ---: | ---: |
| Top 100 on every task | 74 | 0 | 0 |
| Early feedback selector, four per bank | 77 | 18,856 | 3 |
| Later feedback selector, four per bank | 77 | 18,628 | 3 |
| Fixed shifted-confidence priority, four per bank | 77 | 18,508 | 3 |
| Duplicate-history selector, four per bank | 76 | 18,564 | 2 |
| Scrambled-feedback selector, four per bank | 75 | 19,200 | 1 |
| Fixed uncertainty, four per bank | 75 | 19,200 | 1 |
| Random four per bank | 75 | 18,804 | 1 |
| Top 200 on every task | 77 | 36,996 | 3 |

All policies also paid 38,400 top-100 specialist candidate scores. Thus the fixed shifted-priority policy reached 77 correct with 56,908 total specialist scores versus 75,396 for all-200, a 24.5% reduction in this inference component. This excludes generator, old-ranker, source-label acquisition, training and candidate-output prediction costs; it does **not** establish lower total system compute. There were only three beneficial width-200 edits and no harmful ones in the entire fresh target. The later and early selectors chose different tasks (76 of 96 selections overlapped), yet both caught all three. The fixed rule also caught all three.

Later minus early was exactly zero in all 24 banks; later minus fixed shifted priority was also zero. The predeclared five-task and positive-interval improver-growth gate therefore failed. The early/fixed 77 versus all-100 74 difference had bank-bootstrap interval 0 to +6 and occurred in three banks, so it is a useful cost/coverage observation, not robust evidence of a general performance gain. Opened development had 16 beneficial and one harmful width edits across 576 tasks; the fresh target had less edit headroom. The width-edit action is too sparse here to support a convincing positive feedback loop.

A [post-audit forecast diagnostic](analysis/selective-width-forecast-diagnostics-20260918.json) evaluated the frozen heads on those same target rows. Later edit-effect mean squared error was 0.01732 versus early 0.01790; later width-100 Brier error was 0.07120 versus early 0.07465. Scrambled feedback was worse at effect MSE 0.03116. These are small descriptive forecast improvements, not a predeclared gate, and only three positive edit events make calibration and ranking estimates unstable. Crucially, the forecast change yielded **zero** additional correct decisions over early or the fixed priority rule. This is the distinction between an evaluator's numerical fit and an improver's realized growth.

## What changes in the RSI research direction

Keep the validated dual-specialist top-100 evaluator as the tested zero-query seed for this AST mix. Widening to 200 is a scoped inference-budget option; the simple fixed shifted-priority rule is at least as good as both learned selectors on this fresh target and costs slightly fewer candidate scores. Do not promote the width-feedback controller as an improving improver.

For the next test, choose a richer edit catalog where candidate ranking, shortlist formation or search can create gains that width alone cannot. Measure each proposed edit's predicted and externally verified effect on *future held-out tasks*, its harm rate, and its cost. Clone the same base evaluator for early and later improver checkpoints, then test whether the later parent creates a stronger child improver on a second untouched bank. Report evaluator choice accuracy, edit-effect forecast quality, actual child gain, and descendant gain separately. Require a positive result against fixed, scrambled and duplicate-history controls at matched resource vectors before calling it intelligence growth.

Raw evidence: [manifest](runs/selective-width-feedback-transfer-20260918/manifest.json), [frozen selections](runs/selective-width-feedback-transfer-20260918/allocations.json), [task outcomes](runs/selective-width-feedback-transfer-20260918/results.json), and [runner](selective_width_feedback_transfer.py).
