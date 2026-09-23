# Same-base improver transfer: six audited episodes

## Finding

The prospectively declared later-controller test **failed**. I4, which inherited twelve additional effect records from three whole earlier episodes, finished **241/288** on six new 48-task banks. I0, which inherited only the original 60-record source table, finished **242/288**. Paired I4 minus I0 results were **0, −1, 0, 0, 0, 0**; the required five wins and mean gain of two tasks per episode were not met.

Feedback did improve candidate judgment within the new episodes. Each arm began with an evaluator trained on the same two bootstrap tasks. I0 rose from **226/288 to 242/288** through four admitted-feedback rounds. A fresh evaluator using only behavioral memory at round zero scored **236/288**. The I0 improvement over that strong initial component is six selected tasks. This measures a narrow synthetic capability, not general intelligence.

The observed I0 controller exceeded an empty controller (232/288), fixed novelty (239/288), fixed uncertainty under a strict gate (238/288), and fixed disagreement (235/288). Its ten-task lead over empty occurs in just two of six episodes, so the source knowledge's transfer is uneven. I0's particular feedback sequence may be as useful as its learned context rule; a separately declared fixed-sequence control is needed before crediting the table with adaptive intelligence.

## Protocol and verification

[The protocol](EXPERIMENT-seed-improver-transfer.md) was saved before the six new task sets were generated. The source/controller state was also frozen and hashed before generation. I0, I2, I4, scrambled I4, empty, online updating I0/I4 and five fixed tactics all started from the same fresh evaluator per episode. Every arm received **48 new candidate labels per round for four rounds**, identical bootstrap information, the same admission bank, and the same fixed V67/V73 candidate pools. Final predictions were frozen before final labels opened. The same argmax decision rule served admission and deployment; the prespecified fixed uncertainty control alone used its previously strongest strict gate.

All **six replay audits passed**, each reconstructing 268 candidate-source calls, twelve policy arms, five checkpoints and the 192-label allowance. An end-to-end contract check on an older development bank passed. Replay verifies recorded decisions with the same host interpreter; it is not independent proof of program semantics or universal correctness. Across the source, three donor runs and six new runs, all 1,290 public-example sets were distinct.

## Scores by independent episode

Each score is correct chosen programs out of 48. I0 and I4 share the same round-zero evaluator in every row.

| Seed offset | Reachable | I0 start | Initial behavior | I0 final | I2 final | I4 final | I4 scrambled | Empty | Fixed novelty | Fixed uncertainty |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3000 | 41 | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 |
| 4000 | 41 | 38 | 40 | 41 | 40 | 40 | 41 | 38 | 38 | 40 |
| 5000 | 40 | 33 | 39 | 40 | 40 | 40 | 40 | 33 | 40 | 40 |
| 6000 | 42 | 40 | 40 | 42 | 42 | 42 | 42 | 42 | 42 | 40 |
| 7000 | 40 | 37 | 39 | 40 | 40 | 40 | 39 | 40 | 40 | 40 |
| 8000 | 39 | 38 | 38 | 39 | 39 | 39 | 39 | 39 | 39 | 38 |
| **Total /288** | **243** | **226** | **236** | **242** | **241** | **241** | **241** | **232** | **239** | **238** |

I0 had 7 positive and 1 net negative checkpoint transitions across 24 possible rounds; 16 proposals passed its admission gate. I4 had 7 positive and no net negative transitions, with 15 accepted updates. Its final deficit comes from a different acquired feedback path in episode 4000, not from a simple monotone decline. Online updating I4 finished **240/288** and online updating I0 finished **236/288**. Neither improved the final endpoint over its frozen counterpart.

The totals are almost at the candidate-pool ceiling: mixed tasks 135/144 reachable, AST tasks 72/72, new changed-arithmetic tasks only **36/72**. I0 selected 135, 72 and 35 of those respectively. I4 selected 135, 71 and 35. Half the changed-arithmetic tasks lack any correct candidate under the capped generators; no evaluator can fix that with ranking alone. This is a distinct generator weakness.

## What the controller learned and where it failed

The original 60-record table has twelve source observations for each of five feedback tactics. I0 usually acquired disagreement feedback twice, then uncertainty or combined feedback. Its sequence beat every fixed single tactic in the pooled result, but this comparison does not isolate adaptive routing from that favorable sequence.

The twelve appended records in I4 were collected by earlier online controllers, mostly after choosing disagreement or combined feedback. There were no new observations for uniform or novelty. The append moved I4 toward uncertainty in the early rounds of all six new episodes. Scrambling just those twelve added utility values produced **241/288**, the same pooled final score as I4. This is consistent with sparse, policy-selected effect observations failing to add reliable transferable information. It is an inference from the recorded choices, not a causal proof of the mechanism.

Admission correctness and probability error still provide useful gates, but they do not establish the quality of the improver's *predicted edit effects*. The next test needs an explicit edit-utility prediction endpoint and a balanced way to observe alternative tactics. Accepted changes should be judged by sealed downstream performance and task losses, not by admission scores alone.

## Cost

Per new episode, the two-task bootstrap used **22–26 candidate labels**; each arm bought **192 improvement labels**. The common admission bank contained **374–452 candidate labels** depending on the episode. Each arm fit five evaluator states and assessed admission five times. Public candidate generation took **216–232 seconds wall time per episode with four workers** in these runs; source acquisition and audits cost extra. The six runs occurred concurrently, so these wall times are not additive computer-use charges.

The original source archive opened **732 unique candidate labels** across its search. The three donor studies together opened **2,586 unique feedback labels across all their compared arms** (854, 832 and 900). For the particular online donor policy, its bootstrap plus allowance plus shared admission candidate count was 616, 626 and 648 per donor respectively. These inherited-data costs are separate from the 192-label transfer allowance. Their final scoring, candidate generation and repeated model fitting add further cost. Comparing policy scores only at equal *new* labels therefore does not settle total cost efficiency.

## Research decision

The best observed transferable seed in this comparison is **I0 with the ensemble evaluator, argmax choice and proper-score tie retention**, but it is an **unpromoted candidate**, selected from the observed comparison set. Its useful source knowledge and evaluator gains are real within this benchmark; a stronger, more mature improver was not established. The active goal remains open.

Next, compare this candidate with a frozen four-round tactic sequence, full-table scramble, fixed tactics and a controller trained on balanced tactic trials, all on fresh episodes with lower feedback budgets. This tests whether feedback improves the policy for *choosing improvements* before the evaluator saturates. Separately, improve candidate coverage on new mechanisms so that evaluator and generator failures remain distinguishable. A later parent must also demonstrate that it creates a better child improver from an identical base on untouched tasks.

## Artifacts

- Machine-readable scores, paired task outcomes, update trajectories and costs: `analysis/seed-transfer-summary.json`.
- Frozen inherited I0/I2/I4 states: `analysis/seed-transfer-inherited-states.json`.
- Rebuild summary: `.venv/Scripts/python.exe summarize_seed_transfer.py`.
- Six run directories: `runs/seed-transfer-3000/` through `runs/seed-transfer-8000/`, each with `audit.json`, source snapshot, frozen loops and final labels.
- Adjacent literature: `EVALUATOR-LITERATURE-UPDATE-2026-09-17.md`.
