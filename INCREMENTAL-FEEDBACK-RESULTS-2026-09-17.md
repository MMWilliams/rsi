# Incremental feedback: evaluator and improver growth

The first feedback loop is implemented and tested. Four feedback rounds produced five checkpoints. It did not establish net intelligence growth: evaluator solution choices did not improve, and the final improver regressed. There was a narrower improvement in evaluator probability error and rejection of a harmful edit on the focused AST panel.

## Experiment

The evaluator learns a task-balanced logistic correctness estimate from verified candidate outcomes. Its features describe program operations, length and source. The improver learns a table of observed gains and harms for ten authored scoring-policy edits. Every checkpoint starts with the same frozen V67+V73 base, proposes two edits, and uses the designated evaluator to choose an edit or retain the base. Checkpoints are crossed with the initial evaluator/improver to isolate their effects.

The initial evaluator used 12 previously inspected development tasks. Four subsequent rounds accumulated 24, 36, 48 and 60 feedback tasks from a previously inspected archive. These are development data, not fresh confirmation. The evaluator was refitted deterministically on cumulative feedback at each checkpoint; the edit-effect table retained observed utility. Candidate generators and edit vocabulary were fixed.

All checkpoint predictions and choices were frozen before fresh oracle labels were computed. The first panel contained two new mixed-family banks, 24 tasks total. Because its frozen base already solved every reachable task, a second prospectively specified AST panel used two further seeds and the unchanged checkpoints. No task was filtered according to its outcome. Report the two panels separately.

## Checkpoint results

Counts are correct solutions out of 24 for each panel. “Improver” holds the evaluator fixed at E0; “joint” changes both components. Each improver trial resets to the same base.

| Feedback round | Mixed evaluator choices | Mixed improver / joint | AST evaluator choices | AST improver / joint |
| --- | ---: | ---: | ---: | ---: |
| 0 | 21 | 22 / 22 | 5 | 11 / 11 |
| 1 | 21 | 21 / 21 | 5 | 7 / 7 |
| 2 | 21 | 22 / 22 | 5 | 11 / 11 |
| 3 | 21 | 22 / 22 | 5 | 11 / 11 |
| 4 | 21 | 21 / 21 | 5 | 7 / 10 |

The mixed frozen base scored 22/24, with only 22/24 tasks reachable by the saved pool. It offered no positive reranking headroom. The AST frozen base scored 11/24 with 19/24 reachable, leaving eight reachable failures for a better decision process to address.

On AST tasks, task-balanced Brier probability error fell from 0.4341 to 0.3696 (about 14.9% relative), but evaluator solution selection stayed at 5/24. On mixed tasks the error worsened from 0.0284 to 0.0382. These probability-error changes do not by themselves establish better calibration or general judgment.

With the final improver held fixed on AST, replacing E0 with E4 improved outcomes from 7/24 to 10/24. E4 retained the base on one bank instead of accepting an edit that caused three failures. This is a conditional evaluator benefit. It still fell short of the initial improver/evaluator's 11/24. Holding I0 fixed and replacing the evaluator preserved 11/24. Neither component demonstrated replicated net growth over the initial system.

## What blocked growth

Post-outcome diagnostics, not used for fitting or checkpoint selection, found two concrete limitations:

1. The evaluator's features collapse different programs together. On 14/24 AST tasks, at least one feature vector belonged to both a correct and an incorrect candidate. This model cannot distinguish those candidates from these features. Program operation counts and length omit information needed to judge behavior.
2. The improver's global effect table learned a weak average across task families. Its final favored `more_not` edit had only +1 net gain over 60 feedback tasks, including three harms. On the AST panel that edit scored 7/24, below the base's 11/24. Other existing edits could reach 16/24 on these same pools, so useful edits existed but were not proposed or chosen correctly. This 16/24 is an oracle-informed retrospective diagnostic, not an achieved policy result.

The failure is therefore measurable: feedback changed the stored estimates, but those estimates did not reliably improve decisions on new tasks. No checkpoint is promoted as intelligence growth.

## Next incremental change

Keep the tested baseline. Add an evaluator that can distinguish candidate behavior using semantic structure and budgeted discriminating tests. Learn edit effects conditioned on task-visible context rather than one global mean, and record uncertainty and harmful outcomes before proposing an edit. Compare each change independently against this pilot and then cross the components. Select or reject changes on a separate admission bank; reserve new confirmation banks for growth measurement. The inspected banks in this report become diagnostic/development evidence.

The next success criterion remains external: the new evaluator must improve choice utility on identical pools, and the new improver must produce larger gains from the identical base with the same proposal allowance and declared resource budget. A better internal score alone cannot pass.

## Verification and scope

- `runs/incremental-feedback-20260917/`: mixed panel; replay audit passed.
- `runs/incremental-feedback-ast-20260917/`: focused panel; replay audit passed.
- Each audit regenerated 48 candidate-source calls, checked 430 feedback candidate labels, and reconstructed all five checkpoints and decisions.
- Removing all hidden task fields and references left every decision identical in both runs.
- Each run used 1,200 logistic optimization iterations, 1,680 edit-by-feedback-task evaluations, and the same two-edit proposal allowance. Generation timings and candidate counts are archived. Historical source acquisition and candidate generation must be charged for end-to-end efficiency claims.
- The audits replay the same host interpreter; they do not provide an independently implemented correctness oracle. Hash-chain ordering and code separation enforce this local measurement contract, not a sandbox against a malicious learner.
- One feedback curriculum, small synthetic banks, fixed features and authored edits. This does not test new primitive invention, child-improver growth, subjective awareness or general intelligence.

Implementation: `incremental_feedback.py`. Diagnostic output: `analysis/incremental-feedback-diagnostics.json`. Protocols: `EXPERIMENT-incremental-feedback.md` and `EXPERIMENT-incremental-feedback-ast.md`.
