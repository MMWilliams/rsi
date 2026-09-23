# What improved the improver? Six lower budget episodes

## Finding

The declared tests for a context-dependent improver and a stronger balanced-feedback table **failed**. With only 16 new candidate labels per round, I0 and a fixed sequence (disagreement, disagreement, uncertainty, combined) made **identical tactic choices and final program predictions in all six fresh episodes**. I4 chose uncertainty in all four rounds of every episode and made **identical final predictions** to fixed uncertainty. Their apparent gains are gains from effective fixed feedback tactics under these case distributions, not evidence that the controller adapted its tactic to the case.

The final pooled scores out of 288 tasks were I0 **241**, its fixed sequence **241**, full-table scramble **240**, balanced-table B0 **242**, I4 **244**, and fixed uncertainty **244**. The strongest initial single evaluator, behavioral memory, scored **243**; the fixed candidate pools contained correct programs for **247** tasks. The best final result exceeded that strong initial evaluator by one task. I0 improved its own initial ensemble from **237 to 241**, but finished below initial behavioral memory. This is a scoped outcome on synthetic program tasks.

## Prospective protocol and audit

The [protocol](EXPERIMENT-seed-low-budget-control.md), controller states and six seeds were frozen before new tasks were generated. Every arm started with the same fresh two-task evaluator in its episode. The ten arms bought exactly **16 labels per round for four rounds**, shared each episode's candidate pools and admission tasks, used ensemble argmax at admission and deployment, and used the same probability-error tie retention gate. Final predictions at all five checkpoints were frozen before final labels opened.

All **six replay audits passed**, each reconstructing 268 candidate-source calls, ten arms, five checkpoints and exact label counts of 0, 16, 32, 48, 64. An end-to-end contract check on an older development bank passed. Replay uses the same host interpreter; it checks reproducibility and label access rather than an independent semantic implementation.

## Full comparison

Each score is the count of correct chosen programs out of 48. Candidate reachability is reported separately.

| Seed offset | Reachable | I0 start | Initial behavior | I0 | Static sequence | Full scramble | B0 | I4 | Fixed uncertainty |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 9000 | 40 | 38 | 40 | 39 | 39 | 38 | 40 | 40 | 40 |
| 10000 | 41 | 39 | 40 | 41 | 41 | 39 | 39 | 41 | 41 |
| 11000 | 41 | 39 | 41 | 39 | 39 | 39 | 41 | 41 | 41 |
| 12000 | 42 | 40 | 41 | 39 | 39 | 41 | 41 | 41 | 41 |
| 13000 | 41 | 40 | 41 | 41 | 41 | 41 | 40 | 40 | 40 |
| 14000 | 42 | 41 | 40 | 42 | 42 | 42 | 41 | 41 | 41 |
| **Total /288** | **247** | **237** | **243** | **241** | **241** | **240** | **242** | **244** | **244** |

The predeclared I0 minus static differences were **0, 0, 0, 0, 0, 0**. I0 minus scrambled was **+1, +2, 0, −2, 0, 0**: two wins, one loss, and only +1 task pooled. B0 minus I0 was **+1, −2, +2, +2, −1, −1**: three wins and three losses. None passed its screen of four wins and at least one correct task per episode on average. I4's higher pooled score does not establish a better adaptive controller because its decisions were exactly those of fixed uncertainty.

I0 accepted 14 of 24 possible updates across the six episodes, but only five gave a positive held-out correctness step and one caused a net negative step. I4 accepted 16, with four positive and one net negative step. Admission acceptance and final improvement are separate measurements.

## Direct measurement of edit judgment

The five fixed-tactic arms used the same starting evaluator and 16-label first-edit allowance in each episode. Their candidate admission measurements provide five tested edit outcomes for that one common starting point. The predicted scores of I0, its scramble, B0 and I4 were logged before the outcomes were compared. For each controller, the selected first action's child admission measurement exactly matched the corresponding fixed arm's measurement.

| Controller | Mean absolute predicted utility error | Mean regret versus best tested first edit | Selected a best tested edit |
|---|---:|---:|---:|
| I0 | 0.0247 | 0.0266 | 3/6 |
| I0 full scramble | 0.0266 | 0.0324 | 3/6 |
| B0, with fifteen balanced first-edit records | 0.0282 | 0.0162 | 3/6 |
| I4 | 0.0253 | 0.0162 | 3/6 |

Utility and regret are measured per admission task: correctness gain minus 0.25 times harmed-task count, divided by 36. B0 had lower first-edit regret than I0, but worse absolute utility prediction error and no consistent final transfer gain. Six first-edit states are too few to establish a reliable edit evaluator. The first-edit admission metric is also distinct from final held-out task correctness after four rounds.

## Why this comparison has limited headroom

The candidate pool reached **139/144 mixed**, **72/72 AST**, and only **36/72 changed-arithmetic** tasks. In the AST panel there was no generator failure; behavioral memory was already strong. In the changed-arithmetic panel half the tasks lacked a correct candidate under the capped generators. A better ranking evaluator cannot solve an unreachable task. The next benchmark must preserve this generator/evaluator separation and create more cases where correct candidates exist but evaluation is genuinely difficult.

Every new episode used **22–32 bootstrap candidate labels**, 64 improvement labels per arm and **330–410 common admission candidate labels**. Public candidate generation took about **249–256 seconds wall time per episode with four workers** in these concurrent runs. The original 60-effect I0 table came from a separately acquired source archive. B0 reused three earlier donor episodes to add fifteen matched first-edit effects; those earlier oracle labels, candidate generation and fits are additional source costs. Equal new-label allowances do not imply equal total cost.

## Research decision

No adaptive improver is promoted. The older learned controllers collapse to fixed tactic policies across the tested episode range. The balanced update improved one edit-ranking diagnostic and failed the declared final screen. The strongest observed executable policy here is the **fixed uncertainty** tactic, tied with I4 at 244/288, while the single initial behavioral evaluator scored 243/288. No configuration has established a compounding improver or a universally optimal seed.

The next design should vary task mechanisms prospectively so that the best feedback tactic can genuinely change with case context. It should accumulate matched, budget-specific edit outcomes across such cases, estimate uncertainty and harm for each edit, and transfer the resulting policy to untouched mechanisms. It must also improve candidate generation on the changed arithmetic cases. Only a later policy that creates a stronger *child improver* from the same baseline will support the positive feedback claim.

## Artifacts

- Machine-readable episode outcomes, action-level utility, paired screens and costs: `analysis/seed-low-budget-summary.json`.
- Frozen controller states: `analysis/seed-low-budget-states.json`.
- Runner and auditor: `seed_low_budget.py`; rebuild report data with `.venv/Scripts/python.exe summarize_seed_low_budget.py`.
- Six sealed run directories: `runs/seed-low-9000/` through `runs/seed-low-14000/`, each containing source snapshot, frozen loops, final labels and a passed audit.
