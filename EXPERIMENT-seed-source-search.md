# Seed source search: randomized public examples

Freeze before generating source banks. This is discovery and admission evidence, not final confirmation.

Generate six bootstrap tasks, 48 feedback-reservoir tasks and 18 admission tasks from the six existing semantic families, using seeds 205001, 205002 and 205003. Generate each task with zero fixed visible examples and 24 random examples; reveal eight as public examples and retain sixteen as host oracle examples. Cap candidates at sixteen per source from V67 and V73, deduplicating by program in fixed source order. No task is filtered or replaced according to solver outcomes.

Evaluator components: lexical logistic, structural logistic, behavior-memory nearest neighbors, equal structural/behavior ensemble, and ensemble with a 0.12 incumbent bonus. Feature construction accepts public examples and candidate programs only. Behavior probes are 256 unlabeled characters anchored to the public alphabet block. The correct task predicate is never supplied to the evaluator.

Feedback tactics: deterministic random order, predictive uncertainty, evaluator disagreement, distance from previously labeled candidate behavior, and an equal normalized disagreement/novelty mixture. Each tactic buys four complete task candidate-label sets per round for four rounds. Opening all candidate labels counts candidate oracle executions separately; equal task purchases do not imply identical CPU cost. Three driving evaluators (structural, behavior, ensemble) cross the five tactics. All five evaluator components are scored for each checkpoint.

Integration comparisons: unconditional replacement; strict aggregate admission improvement with incumbent retention on ties; and admission improvement without regressions in any observable alphabet-block group. Gates compare evaluator checkpoints, not final-bank outcomes. Report update decisions, selected programs, held-out admission correctness, probability error (for probability-valued components only), proposal costs and full label-access logs.

The source search selects a seed by final admission utility, then fewer regressions, then lower oracle executions, then alphabetical driver/tactic name. Tied gates prefer retention, then strict, then replacement. The strongest static tactic and initial frozen evaluator remain controls for a later separately declared confirmation episode. No final bank exists in this source search. Findings must be labeled discovery until reproduced on fresh confirmation episodes.
