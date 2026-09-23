# Prospective focused-feedback evaluator checkpoint test

Frozen before generating or scoring seeds 902486 through 902497 on 2026-09-18.

## Question and scope

Does an evaluator trained to correct its own past query mistakes choose more useful exact output calls on new synthetic mixed banks? This tests **evaluator growth**, not autonomous improver growth. The rule and its weight were researcher specified after inspecting earlier banks.

## Source and checkpoints

- Train E0 with interaction ridge penalty 100 on the 576 earlier `source_rows()` examples.
- Use the six previously opened admission banks (288 tasks) as verified feedback. Each task supplies a no-query and one-query counterfactual from the external exact oracle. This is more feedback than an eight-call deployment would observe, and its source acquisition cost must be reported.
- Ordinary E6 retrains on all 288 admission rows at weight 1.
- Focused E6 gives weight 4 to admission tasks where E0 bought a query that had zero or negative marginal gain; other admission rows have weight 1. E0 chooses eight calls per admission bank before these outcomes are used.
- Scrambled E6 rotates gain labels within each public mechanism block before training, preserving row count and mechanism mix.
- The fixed transform+mutation schedule and deterministic random eight-call schedule are controls. No model sees the new bank oracle labels before choices are frozen.

## New evaluation

Generate 12 independent 48-task mixed banks, six mechanisms, one visible and 23 hidden examples per task. Candidate generation and selection use the existing full-width AST branch, public-block temperature route, replay AST ranker, top-20-entropy probe, and the same eight predicted probe inputs per task. Each policy receives eight true output calls per bank. Freeze all candidate pools, scores, predicted outputs, checkpoint parameters, and allocations before final scoring.

The primary endpoint is focused E6 minus E0 in oracle-correct final choices across 12 banks. Report paired bank differences and exact bank bootstrap interval. A positive promotion screen requires total gain at least +8, at least eight positive banks, no more than two losing banks, and a positive lower interval endpoint. It must also beat ordinary E6 and scrambled E6 in total. No descriptive improvement in prediction loss alone qualifies. Report no-query, one-query-for-every-task, and hindsight eight-query results as cost-separated references.

The secondary endpoint is forecast mean squared error for marginal one-query gain on the common 576 tasks. Report top-eight call overlap, mechanism allocation, selected marginal gain, candidate labels checked, predicted output cells, generation time, and true output calls. The exact oracle and holdout labels are outside the model write path.

## Interpretation

A successful focused E6 would support scoped feedback-trained evaluator growth on this task contract. It would not establish that an improver can invent the rule, create a better child improver, or transfer to research, cybersecurity, social-good, or policy work.
