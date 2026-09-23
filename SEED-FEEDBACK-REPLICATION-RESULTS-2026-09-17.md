# Incremental evaluator growth: three audited episodes

## Finding

Feedback can improve this evaluator's selection of programs from a fixed candidate pool. The predeclared policy improved from **136/144 to 142/144** across three episodes. Its per-episode gains were **0, +6, 0**. An exploratory inherited-controller policy reached **143/144**, the entire reachable pool across these banks, from the same initial 136/144. The strongest initial single evaluator, behavioral memory, already scored **139/144**.

This is evidence of a scoped evaluator capability gain. Stable improvement of the improver itself is not established. The best inherited controller exceeded the best fixed feedback policy by only one final task. Updating that controller during the loop did not improve its final score over freezing its initial inherited knowledge. The shared finite program domain and three learning episodes do not establish general intelligence or recursive self-improvement.

All three replay audits passed. Each replay reconstructed 276 candidate-source calls, 32 policies, and five checkpoints. These audits use the same host interpreter; they verify reproducibility and recorded decisions, not an independent semantic implementation or an operating-system isolation boundary.

## What was allowed to improve

Each episode started with a fresh bootstrap, feedback reservoir, admission bank and final bank. The V67/V73 candidate generators and candidate pools stayed fixed. The evaluator learned from verified candidate labels. An improver selected the next feedback tactic, trained a candidate evaluator, and used an admission gate to decide whether to retain it. The online controller also updated its estimates of which feedback tactics produce useful changes.

Every arm bought exactly **48 new candidate labels per round for four rounds**. Admission used the same choice rule that would execute on final tasks. Final choices for all checkpoints and arms were frozen before final labels were opened. The final bank was never an update gate.

The primary policy remained **novelty feedback + maximum-score choice + retention with probability-error tie breaking**, as declared before the first episode. The two replications changed seeds only. The newly observed winner is an exploratory candidate, not a retrospectively successful primary.

## Incremental curves

Each cell is the number of correct selected programs out of 48. Round 0 is before the 192 improvement labels.

| Policy / episode | R0 | R1 | R2 | R3 | R4 |
|---|---:|---:|---:|---:|---:|
| Predeclared primary / original | 47 | 48 | 47 | 47 | 47 |
| Predeclared primary / replica 1 | 42 | 42 | 46 | 46 | 48 |
| Predeclared primary / replica 2 | 47 | 47 | 47 | 47 | 47 |
| Online inherited controller / original | 47 | 47 | 46 | 47 | 48 |
| Online inherited controller / replica 1 | 42 | 43 | 47 | 48 | 48 |
| Online inherited controller / replica 2 | 47 | 47 | 47 | 47 | 47 |
| Fixed uncertainty, strict gate / original | 47 | 47 | 48 | 48 | 48 |
| Fixed uncertainty, strict gate / replica 1 | 42 | 44 | 44 | 47 | 47 |
| Fixed uncertainty, strict gate / replica 2 | 47 | 47 | 47 | 47 | 47 |

Replica 1 contains successive useful evaluator updates. Original-episode regressions show that an admission gate can accept changes that harm unseen tasks. Replica 2 starts at its reachable ceiling: one task has no correct candidate in the pool, so evaluator updates cannot solve it.

## Ranked observed policies

All rows choose the candidate with the maximum ensemble score. Ranking is descriptive: final correctness, then summed checkpoint correctness, then name. Ties and correlated controls should not be interpreted as independent discoveries.

| Rank | Feedback policy | Gate | Final /144 | Gain from E0 | Net harmful steps |
|---:|---|---|---:|---:|---:|
| 1 | Inherited controller, updated online | Probability-error ties | 143 | +7 | 1 |
| 2 | Inherited controller, frozen | Probability-error ties | 143 | +7 | 1 |
| 3 | Fixed disagreement | Probability-error ties | 142 | +6 | 1 |
| 4 | Fixed uncertainty | Strict accuracy | 142 | +6 | 0 |
| 5 | Scrambled inherited controller | Strict accuracy | 142 | +6 | 0 |
| 6 | Fixed novelty; predeclared primary | Probability-error ties | 142 | +6 | 1 |
| 7 | Fixed combined novelty/disagreement | Strict accuracy | 142 | +6 | 0 |
| 8 | Fixed novelty | Strict accuracy | 142 | +6 | 0 |
| 9 | Fixed uniform | Strict accuracy | 141 | +5 | 1 |
| 10 | Fixed uniform | Probability-error ties | 141 | +5 | 3 |

“Net harmful step” means total final correctness fell from the preceding checkpoint. A zero-net step can still swap a correct answer for an incorrect one. The online winner had two steps containing a lost task, including one net-negative step; it recovered both by the end. The strict uncertainty control had no task-loss steps in these three episodes.

The online and frozen inherited controllers have the same final outcomes. Online updating improves the intermediate curve in replica 1; that advantage needs separate confirmation. Under the strict gate the frozen inherited controller scores 138/144, below the scrambled control at 142/144. Controller quality depends on its integration gate; there is no unconditional inheritance result.

## Attribution

| Question | Evidence | Interpretation |
|---|---|---|
| Did candidate generation improve? | Pools fixed at every checkpoint; reachable totals 48, 48, 47. | Gains here are selection gains. |
| Did the evaluator improve? | Primary 136 to 142; best observed policy 136 to 143. | Yes within these banks, with most headroom in one episode. |
| Does learning beat a strong frozen evaluator? | Initial behavioral evaluator 48, 44, 47; best learned policy 48, 48, 47. | Four extra tasks, all from replica 1. |
| Is an inherited improver better than fixed feedback? | Best inherited 143; best fixed 142; uniform 141. | Small exploratory advantage; no stable superiority established. |
| Does updating the improver itself improve its final effectiveness? | Online and frozen inherited controllers both 143. | No final-score advantage here. |
| Are improvements retained automatically? | Some probability-error tie promotions regress on final tasks. | Better probability error and admission scores do not guarantee retention. |
| Is this recursive intelligence growth? | No independently verified later-parent-to-better-child-improver result. | Not established. |

The original frozen V67/V73 ranker scores 119/144. Comparing 119 to 143 would mix the benefit of the initial evaluator with subsequent learning. The incremental comparison must start at 136, and the stronger initial behavioral control at 139 must remain visible.

## Cost and measurement limits

| Episode | Common bootstrap labels | Improvement labels per policy | Common admission candidate labels | Final tasks |
|---|---:|---:|---:|---:|
| Original | 46 | 192 | 378 | 48 |
| Replica 1 | 42 | 192 | 392 | 48 |
| Replica 2 | 68 | 192 | 388 | 48 |

Every policy fits five evaluator states and assesses admission five times. The admission label sets are reused; they are a separately reported learning/selection resource. Final scoring and replay cost extra and are not part of the 192-label improvement allowance. Candidate generation, inherited source-data acquisition and training are also additional costs. Equal label allowances do not establish equal total compute. Generation and loop telemetry are retained in each run directory; shared caches and execution order prevent fair compute ranking from the small per-arm timings.

There were no duplicate public-example sets across the three full episodes. Nevertheless, these are related tasks in a shared finite synthetic domain. There are three independent learning episodes, not 144 independent learning trials. No robust uncertainty estimate or significance claim is warranted from three episodes. The 32-arm exploratory comparison adds selection uncertainty. Changed arithmetic constants test a narrow mechanism shift, not open-ended transfer to research, cybersecurity or policy work.

## Decisions for the next experiment

1. Keep evaluator judgment, improver effectiveness and combined-system performance as separate endpoints. Count gains and lost tasks at every accepted update.
2. Carry the online inherited controller forward as an **unpromoted candidate**. Keep strict uncertainty, fixed novelty, uniform feedback, scrambled state and the initial behavioral evaluator as controls. The existing exported source candidate remains unchanged.
3. Isolate improver growth next: freeze I0/I2/I4 knowledge, apply each to identical fresh base evaluators with identical budgets, and compare the resulting evaluators on sealed banks. Transferring an already improved evaluator would confound this test.
4. Preserve the difficult and unsolved cases. Current candidate coverage and initial-evaluator ceilings limit this benchmark. A broader task distribution must be declared before scoring; do not select tasks based on observed failures.
5. Confirm any newly chosen policy on fresh episodes before promotion. A higher training/admission score, more accepted edits, or one recovered regression is insufficient evidence of a better improver.

## Artifacts

- Protocols: `EXPERIMENT-seed-integration-v2.md`, `EXPERIMENT-seed-v2-replication.md`.
- Original run: `runs/seed-integration-v2-20260917/`.
- Replications: `runs/seed-v2-replica-1/`, `runs/seed-v2-replica-2/`.
- Full machine-readable comparison: `analysis/seed-replication-summary.json`.
- Rebuild comparison: `.venv/Scripts/python.exe summarize_seed_replications.py`.
- Measurement contract: `INTELLIGENCE-GROWTH-MEASUREMENT.md`.

The active seed-improver research goal remains open.
