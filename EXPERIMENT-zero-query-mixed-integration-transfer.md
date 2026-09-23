# Frozen mixed zero-query evaluator integration (2026-09-18)

## Question and bank

Can a controller integrate the improved shifted evaluator without losing its familiar-task baseline? Does adding verified mixed edit effects make a later controller create a better child evaluation policy than its earlier self? Generate 24 untouched eight-task banks, seeds 903600–903623, each interleaving four familiar `ast_transition` tasks and four `shifted_ast` tasks, one visible and 23 hidden examples. Candidate generation, E0 scores, and old-order top 100 are common. The primary outcome is final program correctness **before an external output query**. The old pipeline's predicted output/probe preparation is recorded as computation cost; no probe answer enters a zero-query decision.

## Frozen policies and source evidence

- E0; always shifted AB top-100; one pooled familiar-plus-shifted candidate ranker, equal source weights; and an unavailable true-type route for headroom.
- An early public-feature route trained on 288 prior tasks (192 shifted, 96 familiar). A later route uses those plus 192 verified mixed tasks. A type-label-scrambled later route permutes only added mixed labels within each eight-task bank. A balanced duplicate-history route adds 96 familiar and 96 shifted resampled earlier rows, with no new task information. All use an acceptance probability threshold **0.6**, fixed from opened development.
- Paired-effect routes use the same early and later task records, but train to predict the actual AB-minus-E0 final-correctness effect. The later control scrambles the added mixed effects within bank; another adds balanced duplicate history. Accept AB only for a positive predicted effect. These are the improver-knowledge comparisons. Public features include the visible input/output pair, candidate ranker confidences, score differences, ranks and pool size. Task family, reference, seed, task ID, hidden examples and probe answer are excluded from target features.
- Existing shifted ranker A/AB, pooled ranker, and source-panel audits are frozen before target generation. Report source label acquisition, candidate-score counts, candidate pool cost and output-prediction cost. Equal zero-call budget is not equal total compute.

## Decision rules

The general integration gate for the later 0.6 route requires at least +5/192 over always AB, at least 12 positive paired banks, a paired bank interval above zero, familiar subgroup no worse than E0 by two tasks, and shifted subgroup no worse than always AB by eight. Report individual criteria even if the gate fails.

The **improver-growth** gate is separate: the later paired-effect route must exceed the earlier paired-effect route, scrambled added-effect control and balanced duplicate-history control each by at least five tasks; beat the earlier route on at least eight banks; and have paired bank intervals above zero against all three. A fixed public task-type classifier cannot pass this improver gate. Report E0, AB and pooled controls at the same pool and source-cost accounting.

## Execution and audit

Save protocol, script, model and frozen-artifact hashes before scoring final hidden examples. Rebuild the target tasks, candidate pools, predictions, frozen policy choices and final candidate labels in the replay audit. A failed audit invalidates the result. This test can establish a scoped synthetic integration or one later-controller transfer; it cannot establish open-ended RSI, broad domain transfer or matched total compute.
