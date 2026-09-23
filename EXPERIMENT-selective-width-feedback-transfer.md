# Selective width feedback transfer, frozen protocol

Date: 2026-09-18. This protocol is written before the target banks are generated or scored.

## Question

Does verified feedback on widening a dual-specialist candidate evaluator from its old-ranker top 100 to top 200 make the *width-edit improver* better on untouched mixed AST banks? This is a scoped test of edit selection, not a claim of general intelligence growth.

## Source, target, and budget

Use the three previously audited and opened mixed-bank panels in `analysis/selective-width-rows-development-20260918.json` (576 tasks, 16 beneficial and one harmful width-200 edits). Early checkpoint trains on the first two panels (384 tasks). Later checkpoint adds the third (192 tasks). Target: 24 new deterministic mixed banks, seeds 904950–904973, four familiar and four shifted tasks each. Generate candidates using the same frozen generator, old ranker, and specialist model files as the dual-specialist integration test. Never give family or hidden outputs to width selection.

Each selective policy may widen exactly four tasks per eight-task bank. Every task gets the first 100 candidates scored by both specialists. A selected task gets candidates 101–200 scored. Report exact candidate-score counts; compare policies at the same four-selection count and show the varying costs caused by pool lengths. All-100 and all-200 are budget anchors, not matched-budget competitors. Oracle labels are used only after all selections are frozen.

## Policies and promotion rule

- Early and later: fixed two-head histogram gradient boosting classifiers, one per correctness label at width 100 and width 200; score is predicted `P(correct at 200) - P(correct at 100)`. Same hyperparameters as the opened development script.
- Scrambled: same size as later, but added-panel edit effects are scrambled within bank by permuting the width-200 outcomes while retaining width-100 outcomes.
- Duplicate: replace the added-panel rows with 192 resampled early rows, balanced by domain.
- Fixed shifted priority: select the four highest public shifted-minus-familiar confidence tasks per bank.
- Fixed uncertainty: select the four lowest public top-100 specialist confidence tasks.
- Random: seeded random priorities. Oracle four is a retrospective ceiling only.

The improver-growth gate requires later to exceed early, scrambled, duplicate, shifted priority, uncertainty, and random by at least five correct tasks total, with a bank bootstrap 95% lower bound above zero against early and the best fixed policy, and at least eight positive banks against early. Audit must pass. Otherwise keep the earlier/fixed policy and mark improver growth unproved. Report each policy's final accuracy, subgroup accuracy, selected positive/negative effects, acquisition rows, and candidate-score cost. No hyperparameter or threshold tuning on the fresh target.

## Audit

Freeze source and model hashes, target tasks, candidate pools, public records and selected task IDs before scoring. Then score hidden examples using the external exact interpreter. Rebuild public records and selections and re-evaluate every final candidate label in an independent audit pass. Keep the manifest and raw task outcomes.
