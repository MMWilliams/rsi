# Context predicts a little, but did not improve edit selection reliably

## Decision

Do not promote the v6 contextual ridge predictor into the recursive loop. It
failed the screen written before fitting. Keep the predictor, sanitized source
data and full negative result for review. RSI remains unproved.

This is an exploratory offline diagnostic, not a fresh final-bank experiment.
Earlier source summaries were known when the plan was written. Neither final
banks nor transfer/admission outcomes entered model fitting or model selection.

## What changed and why

V5 failed to reproduce v4's inherited-table benefit. Some edits had opposite
effects on different visible task batches at the same search configuration.
That suggested testing whether a table conditioned on current context could
predict useful edits. It did not establish that missing context caused failure.

V6 fits signed candidate-minus-parent correctness on 864 task contexts from nine
source trajectories: 54 menus, 12 edits per menu and 16 tasks per menu. There
are 10,368 task-edit labels but only **122 nonzero effects** (1.18%). All edits
for a task stay in the same source fold. These are correlated observations,
not 10,368 independent trials.

Inputs are 21 fixed statistics of visible input/output examples and eight
bounded parent search settings. Ridge coefficients are separate for each edit.
Nested whole-source cross-validation selects regularization without looking at
the outer held-out source. Controls use no context, only parent settings, or
scrambled training context. All 27 fitted outer ridge models selected alpha
1000, the strongest regularization in the declared grid; the grid was not
expanded after seeing results.

## Results

Ranking utility is the best observed development gain among two proposed edits,
with keeping the parent as a zero-gain option. It is **not final accuracy or
admitted gain**. Entries below average equally over nine source trajectories.

| Model/control | Task-edit MSE | Mean ranking utility, percentage points |
| --- | ---: | ---: |
| Zero predictions, fixed lexical pair | 0.01176698 | 3.1250 |
| Unconditional per-edit means | 0.01174220 | 2.3148 |
| Parent settings only | 0.01174698 | 2.4306 |
| Visible context + parent | **0.01166495** | 2.4306 |
| Scrambled context + parent | 0.01179562 | 2.3148 |
| Uniform random pair, exact expectation | — | 1.1767 |
| Best of all 12 edits, oracle ceiling | — | 3.8194 |

Context reduced MSE by **0.658% relative to unconditional means**, but ranking
utility improved by only 0.1157 percentage points. It tied parent-only utility
and strictly beat unconditional means in **1/9 sources**, below the required
5/9. It also had worse MAE than unconditional means (0.01954 vs 0.01721).
The zero predictor had the lowest MAE, consistent with the sparse labels.
Nonzero-label MSE was 0.97762 for context vs 0.99311 for unconditional means;
these secondary metrics are averaged by source, not by the number of nonzeros.

The fixed lexical pair is `absolute_cost_down` and `absolute_cost_up`. Its strong
result is a useful future control discovered in this diagnostic; it has not
been independently validated as an online policy. Unconditional means always
selected `absolute_cost_up` and `match_cost_down`. Context changed those rankings
occasionally but did not convert its prediction advantage into broad selection
gains. Only **23/54 menus** had any positive existing edit, even with perfect
knowledge of all twelve recorded outcomes.

| Held-out source | Means | Parent | Context | Scrambled |
| --- | ---: | ---: | ---: | ---: |
| v4 / 17 | 2.0833 | 2.0833 | 2.0833 | 2.0833 |
| v4 / 29 | 2.0833 | 2.0833 | 2.0833 | 2.0833 |
| v4 / 43 | 3.1250 | 3.1250 | 3.1250 | 3.1250 |
| v5 / 101 | 1.0417 | 1.0417 | 1.0417 | 1.0417 |
| v5 / 113 | 2.0833 | 2.0833 | 2.0833 | 2.0833 |
| v5 / 127 | 2.0833 | 2.0833 | 2.0833 | 2.0833 |
| v5 / 139 | 3.1250 | 4.1667 | 3.1250 | 4.1667 |
| v5 / 151 | 4.1667 | 4.1667 | 5.2083 | 3.1250 |
| v5 / 163 | 1.0417 | 1.0417 | 1.0417 | 1.0417 |

All entries in this table are offline ranking utility in percentage points.
The declared screen failed. This rules out promoting this particular predictor
under that rule; it does not establish that context is useless or that all
possible selectors would fail.

## Evidence and verification

- Plan: `EXPERIMENT-v6-context-diagnostic.md`, frozen before fitting.
- Run: `runs/context-diagnostic-20260916-v6/`, completed once; measured analysis
  time 0.752 seconds, excluding process startup, snapshot copies and later audit.
- Code: `rsi/contextual.py`, `run_context_diagnostic.py`,
  `audit_context_diagnostic.py`; exact copies retained under the run's `source/`.
- Data: `dataset.json` has public examples, parent settings, signed labels and
  links to prior evaluation request hashes. It excludes programs and hidden
  examples. `analysis.json` retains fold membership, nested errors, permutations,
  scaling, coefficients, features and all predictions. `results.json` retains
  each menu's scores, selected edits, observed gains and all aggregate metrics.
- Journal: twelve timestamped hash-chained events. Manifest seals twelve
  artifacts; hashes detect changes but do not authenticate a hostile host.
- Audit passed: **891 regression fits**, **51,840 predictions**, **45 outer
  model folds**, **54 menus**, their metrics and the advancement screen. The
  auditor uses augmented least squares rather than the trainer's normal equations.
  Source extraction and feature definitions are shared; original labels rely on
  the prior v4/v5 semantic audits. No new oracle query or search was run.
- Verification before fitting: **43 tests passed**, including seven new tests
  for feature boundaries, regression, grouped folds and rejection of forged
  predictions/splits/rankings. Two known PEFT fixture warnings remain.
- No GPU inference, neural training or paid API calls. Prior source acquisition
  cost is already recorded in v4/v5 and cannot be treated as free in later trials.

To audit the completed archive (without refitting the deployed system):

```powershell
.\.venv\Scripts\python.exe audit_context_diagnostic.py runs/context-diagnostic-20260916-v6
```

`run_context_diagnostic.py` creates a new archive and refuses overwrites. Another
run on the same source data is a reproducibility check, not independent evidence.

## Interpretation and next experiment

The measured gap is between predicting effects and choosing edits that reliably
help. Better average prediction error alone did not close it. Sparse signal,
an additive linear model, restricted numerical edits and only nine sources all
limit this diagnostic. Templates can overlap within a source-development split;
whole-source folds do not establish unseen-template generalization. No claim
about research, defensive cybersecurity, social good or policy outcomes follows
from this DSL experiment.

Next, test the available improvement opportunities before building a more complex
selector: predeclare a fresh balanced comparison of numerical edits and verified
macro/library edits, with matched acquisition/search budgets. Include the fixed
absolute-cost pair as a control, plus frozen-library and scrambled-inheritance
controls. If a richer edit space creates useful transferable opportunities,
return to the common-ancestor g0/g3/g6 improver test. Do not reuse v6 outer results
to tune and relabel another predictor as confirmatory evidence.

## Research context

[Empirical performance modeling](https://arxiv.org/abs/1211.0906) already uses
instance features and algorithm parameters; this predictor is not novel simply
because it has context. The target here is a signed coverage change rather than
runtime. [S3Gym](https://arxiv.org/html/2608.31100v1) reports that useful feedback
does not automatically become transferable improvement. Our result supports
keeping prediction and downstream improvement as separate local measurements;
it is not a reproduction of that paper's tasks or methods.
