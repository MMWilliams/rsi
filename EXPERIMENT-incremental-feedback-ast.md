# Focused ranking transfer panel

Declared after the mixed-bank incremental pilot scored 22/24 frozen-base correctness and 22/24 reachability. That ceiling cannot show positive gain from reranking. Retain those results.

Use exactly the same feedback data, five fitted evaluator checkpoints, ten authored edits, and improvement budget. Change only the confirmation task panel to AST-transition tasks, seeds 203303 and 203304, 12 tasks each, eight visible and 13 hidden examples, eight candidates per source. This family is chosen because previously reported AST results showed ranking mistakes despite correct candidates being present. No task is filtered or replaced according to whether the base fails. Report this focused panel separately from the mixed banks; do not claim representative mixed-domain performance.

Freeze checkpoint decisions before opening hidden labels. Use the original incremental-feedback metrics, crossed component tests and replay audit. No fitting or checkpoint selection may use either new panel's oracle labels. A null result remains a null result; this panel is not a license to tune on confirmation data.
