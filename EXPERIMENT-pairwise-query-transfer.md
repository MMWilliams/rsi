# Prospective incremental pairwise evaluator checkpoint test

Frozen before generating seeds 902498–902509 on 2026-09-18.

## Claim under test

Does additional verified feedback make a fixed pairwise query-value learner choose better exact-output calls on fresh mixed banks? This is an evaluator checkpoint test. The pairwise rule was researcher designed after inspecting older banks; it is not autonomous improver growth.

## Checkpoints and controls

- E0 is the retained interaction ridge-100 evaluator trained on the first 576 source tasks.
- P0 is the same 576-task source trained with the pairwise rule: all within-bank pairs where one task has positive one-query gain and the other has nonpositive gain, logistic pair loss, L2 weight .001, Adam learning rate .05 for 300 steps. Public 12-feature vector and six public-block interactions are standardized from training data. No final labels from the target banks enter training.
- P6 adds six previously opened admission banks (288 full task counterfactuals) to P0's source.
- P18 additionally adds the twelve previously opened meta-transfer banks (576 full task counterfactuals), for 1,440 task-level rows total.
- Scrambled P18 has the same row count and training algorithm, with the added 864 gain labels rotated within public mechanism blocks.
- Matched-data interaction ridge-10 and ridge-100 controls train on the same 1,440 rows. Fixed transform-plus-mutation and deterministic random eight-call schedules are budget controls.

The source feedback requires full no-query and one-query counterfactuals for each task, obtained by an exact research oracle at substantial candidate-label cost. Source acquisition, model training and new-bank inference costs are reported separately. Every active policy gets exactly eight true output calls per 48-task bank.

## Fresh bank protocol

Generate twelve new 48-task banks with the same six-mechanism generator, one visible and 23 hidden examples. Use the previously specified full-width AST candidate route, replay AST ranker, public-block temperature route, and top-20-entropy output probe. Freeze task IDs, candidate pools, predicted outputs, evaluator scores, and all eight-call choices before opening final hidden outcomes. The external oracle code and sealed bank are outside evaluator write access.

Primary endpoint: P18 minus P0 in oracle-correct final choices over all 576 tasks, paired by bank. Report total, bank differences and exact bank-bootstrap interval. Promotion requires at least +8 correct tasks, at least eight positive banks, no more than two losing banks, a positive lower interval endpoint, and P18 ahead of both scrambled P18 and the stronger matched-data ridge control. If these fail, keep the earlier checkpoint. P18 versus E0 is a secondary system comparison and cannot replace the incremental endpoint.

Also report forecast mean squared error for the ridge models (pairwise scores are rankings, not probabilities), selected marginal query gain, query distribution by mechanism, candidate reachability, no-query, all-task one-query and hindsight eight-call references, candidate labels, predicted-output cells, generation time, and allocated true output calls. Independently regenerate tasks, pools, predictions, frozen allocations and oracle scores.

## Boundary

A passing P18 would establish only scoped evaluator growth. It would still not show that an improver can discover the pairwise rule, create a better child improver, or transfer to real research, defensive security, public-interest or policy tasks.
