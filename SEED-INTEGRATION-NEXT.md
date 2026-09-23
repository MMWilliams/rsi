# Next seed iteration: integrate the actual evaluated policy

The first confirmation's evaluator can improve while deployed decisions remain fixed. This means the current goal is incomplete.

## Concrete corrections to test next

1. Admit the complete executable decision policy. The current gate judges the evaluator's argmax choices, but deployment then adds a separate 0.05 margin over the frozen candidate. That margin can block a correct newly preferred answer. A policy proposal must include its scoring model and chooser rule; admission and deployment must execute the same rule.
2. Compare direct admitted ranking, the existing margin rule, and an admission-selected decision rule on new banks. The currently observed raw-argmax results are diagnostic evidence, not confirmation of a newly selected deployment policy.
3. Address admission saturation. The strict correctness gate reaches its small-bank ceiling and may reject further useful updates. Test a predeclared lexicographic criterion using non-regressing accuracy and improved proper probability error, with separate confirmation of actual choice gains. Avoid assuming improved probability error alone is intelligence growth.
4. Match candidate-label budgets, not only the number of task label sets. The current uncertainty arm buys 262 candidate labels versus uniform's 206. Preserve that cost difference in the report and cap the next acquisition runs by candidate oracle executions.
5. Retain the simple source-learned static tactic as a strong control. The contextual controller and its online update did not beat uniform; a scrambled controller was stronger. Do not promote that effect model as inherited intelligence growth.
6. Replicate the corrected integration on fresh visible examples, AST tasks and changed mechanisms. Then compare improver checkpoints from the identical base and repeat the feedback loop through more than one genuinely useful accepted update.

The active objective remains the original seed-improver goal. The current artifact is a source candidate with encouraging evaluator transfer and incomplete integration; it is not the optimal seed or a completed RSI result.
