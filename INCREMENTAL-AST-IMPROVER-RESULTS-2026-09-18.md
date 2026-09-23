# Incremental feedback test of the AST evaluator and improver

## Decision

**Do not promote I1 as an improved improver.** Its child solved 28/96 untouched AST tasks with 96 true output calls, versus 25/96 for I0's child and 26/96 for the strongest fixed schedule (one query per task). The I1–I0 difference was +3 tasks, but only **four of twelve banks improved**, one regressed, and the exact bank-bootstrap 95% interval for the sum was **−1 to +7**. The prespecified child-growth gate failed. More decisively, the common new admission feedback did **not** improve either learned parent on the transfer set: I0 parent and child both scored 25/96; I1 parent and child both scored 28/96. This is a small historical-feedback association, not observed incremental intelligence growth.

The result is fully reconstructed by `audit_incremental_ast_improver.py`: 144 new tasks, 72,372 candidate final labels, 578,976 candidate-predicted probe outputs, all 18 eight-call allocations, four parent models and four child models. The audit passed.

## What changed and what was held constant

The fixed system used V67/V73 cap-512 candidate pools, the replay AST ranker, top-20 entropy probe selection, a 12-feature ridge query-value model and an exact 0/1/2-call knapsack with eight calls per eight-task bank. I0 inherited 96 previously verified task effects; I1 inherited those plus 144 more, for 240. The scrambled control retained 240 rows but mispaired the 144 additional effect labels within source stream. The duplicate control filled the same row count by repeating old I0 examples. Ridge penalty 100 and all source files were frozen before new feedback.

Six fresh admission banks supplied 48 tasks. Each parent made a frozen 48-call allocation before labels were revealed. For common child training, the external oracle then provided two true probe outputs per task (**96 shared acquisition calls**) and held-out correctness for the zero-, one- and two-call choices. Each child applied the same ridge update to its parent's source table plus those 48 new rows. Twelve further fresh banks supplied the 96 untouched transfer tasks; each arm spent 96 logical query calls. Historical acquisition is unequal: I0's 96 task-effect rows would require 192 probe outputs, and I1's 240 rows 480, plus final correctness labels and the candidate-generation work. Equal transfer calls therefore do not mean equal total cost.

| Policy | Admission correct / 48 | Transfer correct / 96 |
| --- | ---: | ---: |
| I0 parent / child | 18 | **25 / 25** |
| I1 parent / child | 18 | **28 / 28** |
| Scrambled parent / child | 16 | 28 / 27 |
| Duplicate parent / child | 18 | 24 / 26 |
| Fixed one query per task | 17 | 26 |
| Fixed random two-on-four | 14 | 20 |
| Fixed high entropy two-on-four | 13 | 24 |
| Fixed high disagreement two-on-four | 10 | 23 |

Transfer candidate reachability was 48/96; the zero-query AST ranker solved 9/96. The I1 child changed allocations on six of 96 tasks relative to I1 parent but gained zero correct choices. I0 child changed eight allocations and also gained zero. I1's first- and second-query predicted marginal values correlated only 0.196 and 0.141 with realized marginal correctness. Seventeen first queries and eleven second queries improved correctness; neither step harmed correctness on these particular banks. The current public features convey too little information about where an extra query will be valuable.

## Interpretation and next update

The evaluator can improve final program selection through a fixed output sensor, as the earlier six-mechanism test showed. This study asked the harder question: does feedback improve the **decision rule that spends sensor calls**, and does the later rule produce a better child after identical new feedback? It does not yet. I1's +3 relative to I0 is concentrated in four banks and disappears as evidence of an incremental child gain. The scrambled control's 27/96 is close enough to reinforce that caution.

The next development target is a public-context predictor of (1) whether a candidate pool is reachable, (2) whether the first query will change the selected answer, and (3) whether a second query adds anything after the first. Source-bank cross-validation should compare calibrated value predictions and fixed-budget final correctness against the one-per-task schedule. A new parent/child transfer should proceed only with frozen choices on untouched banks and a protected rule that falls back to one-per-task when predicted uplift is weak. New source labels, final sensor calls and candidate evaluations must remain separately charged. This is a researcher-defined improvement to test; no autonomous edit-vocabulary growth is established.

Protocol: `EXPERIMENT-incremental-ast-improver.md`. Runner: `incremental_ast_improver.py`. Auditor: `audit_incremental_ast_improver.py`. Frozen models, decisions, results and audit: `runs/incremental-ast-improver-20260918/`.
