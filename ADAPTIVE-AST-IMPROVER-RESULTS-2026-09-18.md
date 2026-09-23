# Sequential AST feedback and child-improver transfer

## Decision

**Do not promote the sequential rule as a growing improver.** Its later child solved **32/96** untouched AST tasks at 96 true output calls, versus **31/96** for its earlier child. The paired child gain was +1, with two positive banks, one negative bank, and an exact bank-bootstrap 95% interval of **−2 to +4**. The prespecified recursive growth gate failed. The protected admission gate also rejected the later rule: its parent scored 20/48 versus fixed one-each at 18/48 on six new admission banks, below the required three-task edge. The protected transfer policy therefore used one query per task and scored 26/96.

There is a **scoped evaluator signal** worth following. The raw later sequential child scored 32/96 versus fixed one-each 26/96, with paired bank interval **+1 to +12** and no losing banks. Yet static ridge and a sequential controller that ignored the observed answer each scored 30/96. The two-task conditional edge over those controls had interval **−2 to +7**. Thus the current data support a better raw allocation than one-each on this bank set, while leaving the value of *conditioning on the first output* uncertain. The predeclared admission gate means this rule was not deployed or promoted.

| Transfer policy, 96 calls | Correct / 96 |
| --- | ---: |
| Later sequential parent / child | 30 / **32** |
| Earlier sequential parent / child | 30 / 31 |
| Prior-only sequential child | 30 |
| Static ridge later child | 30 |
| Scrambled-history sequential child | 30 |
| Duplicated-history sequential child | 31 |
| Fixed one-each / random / entropy / disagreement | 26 / 22 / 22 / 26 |
| Protected later child after admission gate | 26 |

On 384 inspected source tasks, leave-one-bank-out development scored conditional sequential **139/384**, prior-only sequential 134, static ridge 135 and one-each 126 at matched 384 calls. The later parent added 144 previously inspected task effects, for 528 versus 384 source tasks. Its historical acquisition would cost 288 additional probe outputs plus final correctness labels and candidate work. All children then received the same 48 new admission task effects, acquired with 96 shared probe outputs. The later parent's transfer score was 30 before that update and 32 after; the earlier parent's went from 30 to 31. Those post-update gains were concentrated in two and one banks respectively and do not pass the recursive child comparison.

The transfer pool contained a correct candidate for 53/96 tasks. The ranker alone solved 10, one query on every task solved 26, and two on every task solved 41 at twice the call budget. On all 96 counterfactual first and second queries, 16 and 15 respectively produced a new correct choice. For the later model, first-query Brier error improved slightly from 0.1282 parent to 0.1276 child; its conditional second-query Brier error worsened from 0.1288 to 0.1291. The conditional model's second-query error was only marginally better than the child prior-only estimate (0.1296), consistent with the uncertain two-task correctness edge.

The full reconstruction audit passed: 144 new tasks, **73,812** candidate final-label checks, **590,496** candidate-predicted output cells and **720** sequential query actions were replayed. It regenerated 28 historical source files, four parents and four children, all pools, rank scores, static allocations, conditional traces, query paths and outcomes. Per-policy live calls were fixed at eight per bank; the audit's counterfactual oracle reads are separately identified from logical deployed calls.

## Implication for the seed improver

The strongest supported *mechanism* remains an external output sensor coupled to a verified candidate pool. The latest sequential policy can sometimes place calls more profitably than a fixed one-each schedule, but it still lacks a reliable feedback-to-better-child effect. Its conditional second-query predictor is weak, and the protected rule correctly withheld promotion on admission. The next edit should target the causal value estimate after the first output: train and validate whether the surviving candidate set, changed top choice and remaining probe partitions predict **actual correctness gain** across held-out mechanisms. A later checkpoint must improve both that forecast and the same-base child transfer under matched acquisition; otherwise it is only another task-specific allocation rule. Broader RSI still requires the system to propose useful evaluator/improver edits, admit them safely, and transfer its own edit know-how beyond this fixed AST query catalog.

Protocol: `EXPERIMENT-adaptive-ast-improver.md`. Source development: `adaptive_ast_query_development.py` and `analysis/adaptive-ast-query-development.json`. Runner and auditor: `adaptive_ast_improver.py`, `audit_adaptive_ast_improver.py`. Frozen run: `runs/adaptive-ast-improver-20260918/`.
