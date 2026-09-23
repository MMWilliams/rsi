# Frozen zero-query shifted-feedback transfer (2026-09-18)

## Question

Can verified candidate feedback improve the evaluator's **first choice before any external output query**, and does a later evaluator checkpoint outperform its earlier parent on untouched shifted AST banks? This tests evaluator growth, not a self-improving edit policy.

## Frozen comparison

- Generate 24 fresh shifted AST banks, seeds 903500 through 903523, eight tasks per bank, one visible and 23 hidden examples. Use the existing V67/V73 widened pool, old ranker, and E0 pipeline.
- Freeze the candidate models already fitted in `analysis/shifted-zero-query-reranker-models-20260918/`: A trained on 96 earlier shifted tasks and 9,566 final-correctness labels; AB trained on A plus 192 later shifted tasks and 28,472 total labels; AB-scrambled preserves A and permutes later labels within task. Keep E0 and familiar top-50 controls.
- All rankers score the same first 100 old-order candidates, except the familiar top-50 control. Select the highest predicted candidate, stable ties by old rank. For the one-call diagnostic, retain the first candidate in this order whose predicted output matches the external probe result. Query calls and pools are identical for all policies. The primary outcome is final correctness at **zero calls**.
- Record first-choice correctness, one-call-each correctness, and budgeted correctness under the already frozen cheap four-call-per-bank allocator; full-pool and top-100 reachability; candidate scores, source label counts, and computation cost. No target oracle labels enter training or selection.

## Decision rule

The A component passes if its zero-call result beats E0 by at least 20/192, improves at least 12/24 banks, and its paired bank interval excludes zero. Incremental evaluator growth passes only if AB beats A by at least 5/192, improves at least 8/24 banks, has a paired bank interval excluding zero, and beats AB-scrambled by at least 5/192. Report each condition even when a gate fails. An improved evaluator does not establish a better improver; that requires a later parent to choose or create a better child from the same base and equal feedback budget on another fresh bank.

## Audit

Write public artifacts and frozen choices before scoring hidden outputs. Save protocol, code, model and artifact hashes. Rebuild tasks, pools, predicted outputs, first choices, oracle labels and summaries in a separate audit command. A failed audit invalidates the result.
