# Predeclaration: G5, the same question with an identifiable target

Written 2026-09-21, after G4 failed and before the G5 seeds are drawn.
Supersedes nothing: `EXPERIMENT-metric-world-transfer-confirmation.md` and its
failure stand as recorded.

## 1. Why G4 failed, and why that was not an answer

G4 asked whether a metric fitted to world co-membership transfers to worlds
centred where training never was. It failed on its control clause: the fitted
metric beat the free rule in fifteen of sixteen gate cells and could not be
told apart from a dimension-permuted copy of itself at budgets 256 and 16384.
The fitted-to-true weight correlation was 0.117 and 0.329.

Two screens then located the cause, and it is not learning.

- `analysis/mechanism-metric-form-20260921.json`. Fitting to squared
  differences rather than elementwise products, which is the form a weighted
  distance actually takes, moved recovery of the true active dimensions from
  0.28 to 0.29. The estimator was not fitted to the wrong thing.
- `analysis/mechanism-metric-identifiability-20260921.json`. The catalog has
  368 atoms and the descriptor has 385 dimensions, so a weighting over those
  dimensions is not determined by the distances among those points. Reducing
  the descriptor to its leading principal components, computed from the
  catalog alone and costing no experience, recovers the weighting: active
  recall 1.00 at width 8 and 16, **0.92 at width 32**, 0.90 at 64, 0.70 at
  128, and 0.33 at the full 385, with Pearson correlation 0.92 at width 16 and
  0.13 at 385.

G4 therefore asked whether an arm could learn something that was not
identifiable from what it was shown. Its failure is uninformative about
transfer, and G5 repeats it with the target made identifiable and nothing else
changed.

## 2. What changes, and what does not

Changed: atom descriptors are the leading **32** principal components of the
same Fourier and Walsh magnitude spectra, re-whitened, computed from the
catalog before any world is drawn. The hidden weighting is sparse over those
32 dimensions, with **8** active, drawn fresh per replication. The width and
the active count were chosen from the identifiability screen above, before any
task was run at that width, and are fixed here.

Unchanged: the catalog, the task form, the budgets, the arms, the splits, the
statistics, the +15 floor, and the requirement that the gate hold at every
budget. `free_cosine` remains unweighted proximity in whatever descriptor the
run uses, so it is reduced to 32 dimensions too and keeps its role as the free
procedure that needs no training worlds.

## 3. Predeclared criterion

**G5.** Two replications, independent seeds, the weighting redrawn for each.
On `new_family_centre`, at k of 1 and 2, and at **every** budget in
{256, 1024, 4096, 16384}:

- `meta_metric` minus `free_cosine` is at least **+15** of 640 with a bootstrap
  interval entirely positive, and
- `meta_metric` minus `meta_scrambled` is positive with a bootstrap interval
  entirely positive.

A single cell failing fails G5, in either replication. No cell is read after
the fact and no budget range is restricted afterwards; G3 was withdrawn for
exactly that and G4 was written to avoid it.

## 4. What a pass or a failure would mean

A pass: an acquired metric over atom behaviour transfers to a region of the
hypothesis space that training was never centred on, beating both the free
procedure with the same present evidence and a permuted copy of itself, at
every budget. That is the one thing nothing in this repository has yet done.

A failure with the target identifiable and recovery at 0.92 would be a
substantive negative rather than a broken instrument: it would say that
recovering the structure of the worlds one has seen is not sufficient to rank
hypotheses in a world one has not.

Either way it is one environment, one task form, one descriptor family and one
class of latent structure, and no forecast is scored.
