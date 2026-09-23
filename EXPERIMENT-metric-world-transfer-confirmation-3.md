# Predeclaration: G6, the same criterion with enough power to read it

Written 2026-09-21, after G5 failed and before the G6 seeds are drawn. G4 and
G5 stand as recorded; neither is re-read.

## 1. What G5 showed

With the target made identifiable (32 principal components, 8 active
dimensions), the fitted metric recovered the hidden weighting at Pearson 0.939
and 0.976, and beat both the free unweighted rule and a dimension-permuted copy
of itself in **fifteen of the sixteen gate cells** in each replication. Both
replications failed the same single cell: k=2 at budget 256, where the margin
over the free rule was +10 [-2, 22] and +11 [0, 22] against a floor of +15 with
an interval required to be entirely positive.

That cell is where the study has least to find and least power to find it. In
replication 1 the *true* weighting beats the free rule there by only
+19 [3, 35], so a floor of +15 asked the fitted metric for four fifths of all
the headroom that exists in that cell; in replication 2 the true weighting is
worth +49 and the fitted metric captured +11 of it, with an interval whose
lower bound is zero. A criterion that is unattainable in one cell is a flaw in
the protocol, of the same species as G3's single-budget gate, and it is
recorded as one.

## 2. What changes

**Only the number of evaluation worlds.** 32 per split instead of 16, so 1,280
tasks per split per replication instead of 640. The floor moves from +15 to
**+30** of 1,280, which is the same effect size per task; nothing else about
the criterion, the arms, the splits, the budgets, the descriptor or the
estimator changes. Seeds are fresh.

This is added power at a fixed effect size, not a narrower gate. No cell is
dropped, no budget range is restricted, and the failing cell of G5 is included
on the same terms as every other.

## 3. Predeclared criterion

**G6.** Two replications, independent seeds, the weighting redrawn for each.
On `new_family_centre`, at k of 1 and 2, and at **every** budget in
{256, 1024, 4096, 16384}:

- `meta_metric` minus `free_cosine` is at least **+30** of 1,280 with a
  bootstrap interval entirely positive, and
- `meta_metric` minus `meta_scrambled` is positive with a bootstrap interval
  entirely positive.

A single cell failing fails G6, in either replication.

If G6 fails again at k=2 and budget 256 while passing elsewhere, the reading is
that a metric acquired from other worlds does not help at the tightest budget
once two mechanisms of the new world have already been solved, and that is a
result about where a prior stops paying rather than a broken gate. It will be
reported as such and the claim will be stated with that exclusion, in the
protocol, before the numbers are read again.

## 4. Accounting

As G4 and G5: wall time, CPU time, peak memory, fitted-to-true weight
correlation, catalog digest, runner hash, and a decision journal per
replication.
