# V5 replication: the inherited-table benefit did not replicate

Run: `inheritance-20260916-v5`, completed once under the declared protocol.
Independent audit passed. The current selector is **not promoted as a better
improver**. RSI remains unproved.

## Intervention and controls

The selection method, edit catalog, macro library and per-source budgets match
v4. Six new source seeds and a fresh 256-task final bank replace v4's three
sources and 128 final tasks. Every source supplies g0/g3/g6, scrambled g6 and
random conditions, all restarting from BASE_CONFIG. All 36 optimization
trajectories closed before the final evaluation.

Selection logging is new, but regression tests against archived v4 code verify
identical operator choices and RNG states. It records why a candidate was chosen
without changing the rule that chooses it. Source code and protocol were held
fixed throughout the run.

## Results

Final tasks solved out of 256; the unchanged ancestor solved 149/256 (58.20%).

| Source seed | Empty adaptive (g0) | g3 | g6 | Scrambled g6 | Random |
|---|---:|---:|---:|---:|---:|
| 101 | 149 | 157 | 150 | 150 | 157 |
| 113 | 157 | 153 | 153 | 149 | 149 |
| 127 | 152 | 150 | 150 | 152 | 149 |
| 139 | 149 | 149 | 149 | 149 | 152 |
| 151 | 149 | 148 | 151 | 150 | 151 |
| 163 | 149 | 149 | 149 | 151 | 149 |
| Mean solve rate | 58.92% | 58.98% | 58.72% | 58.66% | 59.05% |

| Prespecified contrast | Mean difference, percentage points |
|---|---:|
| g6 − g0 | −0.1953 |
| g6 − g3 | −0.2604 |
| g6 − scrambled | +0.0651 |
| g6 − random | −0.3255 |

The declared screen required all four means positive and a majority of sources
with g6 strictly better than **both** g0 and scrambled. Three means were negative;
only source 151 met the joint source criterion (1/6, with 4/6 required).
The screen therefore failed. Its role was to guide the next experiment, not to
certify statistical significance or RSI even if it had passed.

V4's +0.78-point mean g6−g0 difference became −0.20 points on this fresh study.
Do not pool absolute solve rates: excluding earlier templates changed the
remaining task distribution. Six source trajectories share the same final bank;
they are not six independent task banks. Per-source paired-task bootstrap
intervals remain descriptive and are saved with all contrasts in `results.json`.

## What the logs do and do not explain

Source calibration recorded 432 proposals. Of those, 370 had zero net development
gain (85.65%), including three that traded task wins for losses. Across 6,912
task-edit observations there were 47 wins and 36 losses; 65 proposals changed any
task outcome. These observations share tasks within generations and are not
independent training examples.

The outcome does not show that inherited knowledge can never help. It shows
that this unconditional operator table and selection rule did not reliably
transfer its small v4 benefit under this replication. Sparse effects, task and
parent dependence, the selector's ranking rule and the limited edit space remain
candidate explanations. The experiment did not isolate their causal contributions.

New traces make the implemented choice inspectable: beta parameters/draws,
immediate and descendant effect terms, combined scores, exclusions, tie rule,
chosen name, and RNG hashes before and after. They explain why the code chose an
edit; they do not prove why it improved a task or estimate a calibrated chance of
future improvement.

Readable examples:

- `analysis/v5-accepted-edit-explanation.md`
- `analysis/v5-rejected-edit-explanation.md`

Each report links exact journal/evaluation events and records its renderer's
source hash. Repeated requests are distinguished by trajectory label, so their
measured timing is not silently taken from another execution. Reports stay
outside the sealed archive.

## Verification and costs

- Pre-run suite: **36 passed**; two existing tiny-model PEFT configuration warnings.
- Audit: 32 artifact hashes, 3,304 journal events, 1,471 evaluation batches,
  **30,976 search outputs** regraded with the published interpreter and **792
  edit attempts** reconciled.
- All selection draws/rankings, table updates, admissions, transplants,
  final-score lineage, ordering constraints and cost totals reconciled.
- Runtime: 673.09 seconds through result construction; worker request time
  650.79 seconds, of which source acquisition consumed 178.41 seconds.
- Logical charges: 4,059,172 expansions, 289,241,566 primitive executions and
  495,616 oracle examples. Cached work is charged again for replay; oracle counts
  are upper bounds when execution short circuits. These are not FLOPs or energy.
- No neural training, GPU inference or paid model calls were used. No execution
  sensor/replay incident was recorded.

The audit checks recorded outputs and decision arithmetic. It does not rerun
every search or authenticate a host able to replace both evidence and hashes.

```powershell
.\.venv\Scripts\python.exe audit_inheritance.py runs/inheritance-20260916-v5
.\.venv\Scripts\python.exe analysis/summarize_replication.py runs/inheritance-20260916-v5
.\.venv\Scripts\python.exe analysis/analyze_edit_signal.py runs/inheritance-20260916-v5
```

The screen and diagnostic JSON files record source and input hashes. Diagnostics
are post hoc descriptions; the screen itself was declared before the run.

## Next action

Stop treating additional calibration of this unchanged table as the main path
forward. Test whether an edit-effect predictor using visible task properties and
parent configuration predicts held-out source outcomes better than unconditional
averages. Use source data, group splits by source/generation, and keep the final
banks out of fitting and selection. Preserve task wins and losses separately.

A useful predictor must then earn its place through a fresh common-ancestor
intervention with fixed acquisition/downstream budgets and scrambled-context
controls. If prediction fails, revisit the edit space or the information in the
tasks; do not equate a fitted model with an improved improver. This is the next
hypothesis, not a completed repair.

Neural retention, raw large-k coverage, catalog extension, acquisition-inclusive
compute matching and application-domain outcomes remain part of the full RSI
objective. No requirement is waived by this component study.
