# Prospective low-budget test of improver knowledge and edit evaluation

Declared after inspecting the six 48-label-per-round transfer episodes, before generating any new task or candidate in this study. Those earlier tasks are development evidence only.

## Question

Was the I0 controller's advantage caused by its context-dependent effect table, by its commonly chosen sequence (disagreement, disagreement, uncertainty, combined), or by chance under a nearly saturated evaluator? Can a table augmented with balanced first-action comparisons improve edit selection?

Freeze four controller states before new task generation:

- **I0:** the unchanged 60-record source effect table.
- **I0_full_scrambled:** the same 60 state/tactic rows with all 60 utility values randomly permuted using seed 942.
- **Static sequence:** disagreement, disagreement, uncertainty, combined, regardless of context. This sequence was observed in prior episodes and is therefore a strong development-derived control.
- **B0:** I0 plus fifteen first-round records extracted from the three prior v2 donor episodes. For each donor, the five fixed-tactic arms used the *same starting evaluator*; each bought 48 new labels for its first proposed child. Add the child's admission correctness delta minus 0.25 times harmed-task count, divided by admission task count. Reconstruct and verify the common initial evaluator state from saved bootstrap labels; record the same visible-only context for each of the five tactic trials. Do not select donors or records by their final outcomes.

The previous I4 state remains a secondary control. All learned states are transferred without trained evaluator weights.

## Fresh cases and costs

Six full episodes use offsets +9000 through +14000 in steps of 1000 from v2 base seeds 207001..207006. Each has two bootstrap tasks, 48 reservoir tasks, 36 admission tasks, 24 mixed final tasks, 12 AST final tasks and 12 changed-arithmetic final tasks. Public/hidden examples are 8/16; changed arithmetic uses the previously declared `seed_transfer_banks.RULES`. Public candidate sources are V67/V73 at cap 16, program-deduplicated in source order. Do not filter for reachable or favorable tasks.

Every arm buys **16 new candidate labels per round for four rounds**, 64 improvement labels total. Initial bootstrap and common admission labels are separately reported. Compare I0, full scramble, static sequence, B0, I4, and five fixed tactics (uniform, uncertainty, disagreement, novelty, combined). All use ensemble argmax for admission and deployment and the same proper-score tie retention gate. Exact candidate pools, admission bank and final bank are shared within each episode. Freeze final predictions at all checkpoints before opening final labels. Maintain separate gain/loss counts for every accepted update.

## Primary outcomes and interpretation

The primary endpoint is final oracle correctness of I0 versus static sequence and full scramble, paired by complete episode. Evidence for *context-dependent* I0 knowledge requires I0 to beat each control in at least four of six episodes and by at least one final task per episode on average; ties are not wins. B0 versus I0 is a secondary candidate improvement test with the same screen. If screens fail, preserve the null result.

The five fixed arms also form an equal-budget first-edit comparison from the identical base evaluator. Before opening final labels, log each learned controller's predicted utility for all five tactics. After fixed-arm first-edit admissions are measured, score the selected tactic's realized admission utility and regret relative to the best of the five tested edits. The matching fixed and learned action must yield the same first-round child measurement. This is the improver's edit-evaluation endpoint; final task correctness remains the transfer endpoint. Report edit-prediction error, first-step regret, final curves, reachability by panel, full source acquisition cost and replay scope separately.

An observed winner in this study is still selected from a comparison set and needs a later untouched promotion test. Finite hidden examples and same-host replay do not certify universal correctness or broad intelligence growth.
