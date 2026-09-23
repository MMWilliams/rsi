# Frozen confirmation: construction improver growth

Predeclared 2026-09-21, before any bank for this experiment is generated.

## What is being confirmed

`analysis/construction-improver-development-20260921.json` and
`analysis/construction-improver-rotation-20260921.json` show, on opened panels,
an improver that receives only verified history banks and builds everything
itself: it computes the latent complexity partition from its own labels, trains
one specialist per bin, fits its own router, and deploys. Nothing is inherited.

Across a five-fold rotation of the held-out panel, both gates passed in 5 of 5
folds, and the advantage over the free alternative widened monotonically with
history: **9.8, 18.0, 24.8, 37.4, 45.0** at 4, 8, 16, 32 and 48 history banks.
Mean construction growth was 73.4 against 37.0 for the same data pooled.

This protocol tests whether that survives on banks generated after it is hashed.

## Design

- **Improver input**: verified history banks only. No model, partition, router
  or label is inherited from outside the run.
- **Improver output**: a partition, one specialist per bin, a pooled model, and
  a router over them, all fitted on its own history.
- **Zero-knowledge baseline**: **one pooled model trained on exactly the same
  history**, deployed everywhere. Identical data, identical labels, identical
  compute budget, no partition and no router. This is what a researcher would do
  without knowing the partition matters, and beating it is the claim.
- **History-size arms**: 4, 8, 16 and 24 banks. Each size is scored as the
  **expected** per-bank result over strided windows of the history pool, never a
  single draw, for the reason recorded in `COMPLEXITY-IMPROVER-RESULTS`.

## Banks

Fresh seeds, never used. Six families, 48 tasks per bank, 12 banks per panel.

- Replication one: history_a 916100-916111, history_b 916200-916211,
  transfer 916300-916311.
- Replication two: history_a 917100-917111, history_b 917200-917211,
  transfer 917300-917311.

The transfer panel is held out of every history window in both replications.

## Gates

Correct zero-query top choices per 576 tasks, paired at bank level, exact bank
bootstrap.

- **E1, construction beats pooling.** Largest-history built system minus the
  pooled baseline trained on the same history. Pass: gain > 0 and interval
  excludes zero.
- **E2, construction growth.** Largest-history built minus expected
  smallest-history built. Pass: gain >= +6, at most 4 of 12 losing banks,
  interval excludes zero.
- **E3, growth exceeds data volume.** Reported and gated: construction growth
  must exceed pooled growth over the same history sizes. This is the comparison
  that separates a better improver from simply more data, and the routing
  experiment could not make it.
- **E4, monotonicity.** Reported, not gated.

## Reporting rule

**Construction-improver growth is claimed only if E1, E2 and E3 pass on both
replications, each with a passing independent audit.** A single pass is reported
as a single pass. If E2 passes while E3 fails, the claim is limited to more data
helping, not to a better improver, and the results file must say so in its
headline.

## Declared limits

- One synthetic benchmark and one notion of complexity.
- The partition *rule*, bin edges on first-correct rank, is researcher written.
  The improver computes the partition and trains every model, but did not invent
  the rule. This is the remaining purity gap and must be stated in any writeup.
- The complexity bin derives from the base ranker's order, so it is latent but
  not independent of that ranker.
- Strided windows over one history pool are not independent samples.
- Nothing here tests recursive child-improver growth, which failed its own
  screen; see `RECURSIVE-GROWTH-2026-09-21.md`.
