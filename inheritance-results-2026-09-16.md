# Balanced inheritance: a small, inconsistent benefit

Run: `runs/inheritance-20260916-v4/`. Completed once under the declared protocol;
independent audit passed. This component study does **not** demonstrate RSI.

## What changed and why

Earlier source runs tried 24 proposals across twelve edit types, leaving some
types untested. V4 tried all twelve types in each of six generations: 72 proposals
per source, three source seeds. It kept the existing edit language and selector.
Each learned table was then transplanted into the same BASE_CONFIG ancestor with
the same macro library, and received twelve downstream edit opportunities.

All eighteen optimization trajectories closed before the shared 128-task final
bank was scored. There were no weight updates in this experiment. Equal
downstream opportunities do not include the extra cost of acquiring a table.

## Prespecified outcomes

Entries are final tasks solved out of 128. The unchanged ancestor solved 84/128.

| Source seed | Empty adaptive (g0) | g3 | g6 | Scrambled g6 | Random |
|---|---:|---:|---:|---:|---:|
| 17 | 86 | 87 | 86 | 84 | 86 |
| 29 | 84 | 88 | 90 | 87 | 86 |
| 43 | 87 | 84 | 84 | 87 | 86 |
| Mean solve rate | 66.93% | 67.45% | 67.71% | 67.19% | 67.19% |

| Contrast | Mean difference, percentage points | Source differences (17, 29, 43) |
|---|---:|---|
| g6 − g0 | +0.78 | 0.00, +4.69, −2.34 |
| g6 − g3 | +0.26 | −0.78, +1.56, 0.00 |
| g6 − scrambled | +0.52 | +1.56, +2.34, −2.34 |
| g6 − random | +0.52 | 0.00, +3.12, −1.56 |

Later tables did not improve monotonically within every source. The aggregate
g6 advantage over g0 is equivalent to one additional task per source on average.
Source 29 drives the positive mean; source 43 loses. This is weak, heterogeneous
evidence for this table intervention, not reliable improvement of the improver.

The saved `results.json` includes per-source paired-task bootstrap intervals.
For g6−g0 they are −2.34 to +2.34, +0.78 to +9.38, and −7.03 to +1.56 percentage
points respectively. These are descriptive intervals over the shared tasks,
conditional on each trajectory. They are not a source-population interval, a
multiple-comparison-adjusted significance claim, or three independent final banks.

## What the additional evidence tells us

The following diagnostics were computed after completion from existing records;
they did not query new tasks or change selection.

| Source seed | Positive edit effects | Zero effects | Negative effects | Accepted edits |
|---|---:|---:|---:|---:|
| 17 | 8 | 58 | 6 | 3 |
| 29 | 3 | 68 | 1 | 1 |
| 43 | 2 | 67 | 3 | 1 |

Every operator received six trials, but **193/216 proposals (89.35%) had zero
development effect**. Balanced coverage still produced little informative
feedback. Absolute comparison with v2 cannot isolate calibration's causal effect
because the task banks and template exclusions changed.

Later source-only diagnostic, recorded while v5 was running: two of the 193
net-zero proposals changed which tasks were solved, trading wins for losses.
Across all source edits there were 26 task wins and 13 losses in 3,456 task-edit
observations; 25 proposals changed any task outcome. These repeated observations
are not independent examples. Thus "zero effect" above means zero aggregate
development gain, not necessarily identical behavior. Source and analysis hashes
are in `analysis/inheritance-20260916-v4-edit-signal.json`.

### A traceable failure: source 43

The g6 table led to no accepted transfer edits and finished at the ancestor's
84/128. Empty and scrambled tables each accepted two edits and finished at 87/128.
At the unchanged ancestor, `match_cost_down` lost one of sixteen development
tasks in generations 1 and 2 of the g6 transfer. In generation 3, the empty and
scrambled conditions tried that same edit from the same ancestor on the same
development slice: it gained two of sixteen tasks and passed admission with no
net loss. G6 instead tried two edits with zero gain in that generation.

Evidence links: `transfer_trajectories.json`, source 43, g0/g6/scrambled_g6,
generations 1–3; evaluation labels beginning `transfer/<condition>/10043/g3/` in
`events.jsonl`. Recorded request hashes establish the matched parent and task
slice. This shows task-dependent edit effects and missed opportunities in this
run. It does **not** establish that a context-conditioned selector would fix the
problem, nor that stochastic selection alone caused the aggregate outcome.

## Audit and cost

- 33 tests passed before the run, including semantic forgery and ordering tests.
- Independent audit: 32 archived artifact hashes, 1,654 journal events, 736
  evaluation batches, 13,568 selected programs regraded with the published
  interpreter, and all 396 edit attempts reconciled.
- The audit reconstructs table updates, admissions, common-ancestor transplants,
  final-score lineage, contrasts and costs. It does not independently rerun every
  search. Hashes do not authenticate a host that can replace the archive.
- Recorded wall time: 269.55 seconds through result construction; worker request
  time: 260.50 seconds. Source acquisition used 74.83 worker seconds in total.
- Logical work: 1,726,280 search expansions and 126,487,900 primitive charges,
  including replay. Cached work may be charged without executing again; 217,088
  oracle example charges are upper bounds where evaluation short circuits.
- No paid model calls, neural training or GPU inference occurred in this study.

Recheck the archive with:

```powershell
.\.venv\Scripts\python.exe audit_inheritance.py runs/inheritance-20260916-v4
.\.venv\Scripts\python.exe analysis/analyze_inheritance.py runs/inheritance-20260916-v4
```

The diagnostic JSON records hashes of its source script, result file, audit and
artifact manifest. It is outside the sealed run archive and explicitly post hoc.

## Decision and next discriminating tests

Do not promote this selector as a reliable inherited improver. Preserve the small
positive mean and the failing source, and replicate on fresh source seeds and a
fresh final bank before changing the mechanism. More source trials are still
needed to estimate repeatability; this run cannot establish a general effect.

Separately test whether visible task/context information predicts edit effects
better than unconditional operator averages. Compare an explicitly declared
contextual rule against the existing rule and random selection under the same
data-acquisition and downstream budgets. Do not tune that rule on this final
bank. Add per-operator selection scores and random-draw provenance to future
logging so the choice itself is explained, as well as its measured outcome.

The full goal still requires sustained neural coverage, reliable model promotion,
common-ancestor gains across replications, acquisition-inclusive compute controls,
and outcomes in the intended application areas. This study supplies one component
result, not a substitute for those requirements.
