# Frozen candidate-conditioned query-value transfer

Frozen 2026-09-18 before generating seeds 902534-902545. The preceding screen used only two opened, fully audited 12-bank panels (1,152 tasks, 24 banks) and selected `conditioned_interaction_100` by leave-one-bank-out correct final choices (724 versus old frozen allocator 708 at eight calls per bank). These source results are development evidence, not the fresh endpoint. Source feature, training and tie-break code is `candidate_conditioned_query_development.py` and is frozen by hash.

## Task and cost contract

Generate twelve new independent 48-task, six-mechanism banks with one visible and 23 hidden examples each. Reuse byte-identical E0/E1/7-leaf/scrambled candidate rerankers, old full-width AST candidate generator, public-block route, replay AST ranker, top-20-entropy first probe, and candidate-output prediction from the previous transfer. All children use the **same E0 candidate order** and one common probe per task; only eight chosen output-call locations per bank can differ. Save target tasks, pools, output predictions, E0 orders, public features, model coefficients, forecasts and selected calls before any target final label is opened. The research oracle, hidden outputs and candidate final labels remain outside policy input.

## Feedback checkpoints and controls

The initial parent fits `conditioned_interaction_100` on the first 12 opened source banks (576 task-level E0 query-gain labels). The later parent fits the identical rule on all 24 (1,152 labels). A scrambled parent uses the first 12 intact and rotates the second 12 query-gain labels within each public mechanism, preserving family rates but disrupting task-feature credit. A duplicate parent sees the first 12 twice. The old frozen allocator is an independent fixed control. Fit two matched-data controls on all 1,152 source tasks: `old_family_100` using the previous 12 features and `conditioned_family_100` using all 26 features without mechanism interactions. All use exactly eight calls per bank, the same E0 base, the same candidate generation and predictions. Source label acquisition, training time, candidate generation, predicted output cells, rescoring and true calls are reported separately.

## Endpoints and gates

Banks 902534-902539 are admission; 902540-902545 are protected transfer. The primary evaluator endpoint is later versus the old frozen allocator across all twelve fresh banks: final correct choices, selected marginal gain, per-task query-gain MSE, bank differences and exact paired bank-bootstrap interval. Promote the evaluator component only if gain >=8, at least eight positive banks, no more than two losing banks, lower interval endpoint >0, and lower MSE. A matched-data feature claim additionally requires later to beat both old-feature and no-interaction controls on final correctness.

The primary improver endpoint is later-child minus initial-child correct final choices on the six protected transfer banks, after admission. Admission accepts later only if it matches or exceeds initial, incumbent, and old-feature matched-data controls on the first six banks. A positive child-growth claim further requires transfer gain >=4, at least four positive banks, positive lower interval endpoint, and later ahead of scrambled, duplicate, old-feature and incumbent controls. If a gate fails, keep the prior supported checkpoint; report all outcomes and do not revise this threshold after opening labels.

This is a bounded, researcher-written learning rule and synthetic string-task contract. Even a passed component or child gate would not establish autonomous vocabulary growth, cross-domain intelligence or general RSI.
