# Predeclaration: transfer to a region of the space training never centred on

Written 2026-09-21, before the confirmatory seeds are drawn. Development
evidence: `analysis/mechanism-metric-worlds-20260921.json`. Background:
`MECHANISM-GROWTH-RESULTS-2026-09-21.md` §4 (G3 withdrawn), §6, and
`analysis/mechanism-atom-clustering-20260921.json`.

## 1. Why this run exists

Four attempts to transfer to a world built from an atom family no training
world contained have failed. The fifth measurement explains the other four: in
those worlds a family is the *name of an arithmetic operation*, `mod:2:0` and
`mod:16:7` share a label and nothing observable, and unsupervised clustering of
atom behaviour recovers the family labelling at adjusted Rand 0.144. The
holdout asked for generalization across a boundary nothing computable on an
atom can see. No representation defined on behaviour could have crossed it, and
the repeated failure is a fact about how those worlds were built.

This run uses worlds whose latent structure is behavioural, so the question is
answerable either way. A sparse random weight vector over the 385 descriptor
dimensions is drawn once per replication and shown to nobody; a world is a
centre atom and the fourteen atoms nearest it under that weighting, and the
catalog rows those atoms generate. Every atom has a descriptor, including atoms
no training world contained, so a prior stated over the weighting is defined
for them.

## 2. Arms

- `free_set` the solved atoms of the new world, treated as a set.
- `free_cosine` unweighted descriptor proximity to those atoms. It needs no
  training worlds at all and is the rule every claim below is measured
  against, because a built system that loses to a free procedure in its class
  has been withdrawn three times in this repository already.
- `meta_metric` a diagonal metric over descriptor dimensions, fitted to
  co-membership on 400 training worlds.
- `meta_scrambled` the same fitted metric with its dimensions permuted.
- `oracle_metric` the true weighting. Not deployable and not a claim; it is
  reported so the headroom is visible.

Every arm is scored at least as high by its own present evidence as `free_set`
would score it, so no arm can be beaten by the atoms it has already seen.

## 3. Splits

Training worlds are centred on atoms of seven families. Evaluation worlds are
centred on atoms of those seven (`seen_centre`) or on atoms of the two families
no training world was centred on (`new_family_centre`). Test mechanisms are
removed from every training world's solved sample.

## 4. Predeclared criterion, read across the whole budget range

Two replications on independent seeds, with the hidden weight vector redrawn
for each, so what is tested is the method and not one draw. 16 worlds per
split, 40 test mechanisms per world, 640 tasks per split per replication.
Paired bootstrap over tasks, 20,000 resamples.

**G4.** On `new_family_centre`, at k of 1 and 2, and at **every** budget in
{256, 1024, 4096, 16384}:

- `meta_metric` minus `free_cosine` is at least **+15** of 640 with a bootstrap
  interval entirely positive, and
- `meta_metric` minus `meta_scrambled` is positive with a bootstrap interval
  entirely positive.

Both conditions, at all four budgets, at both k, in both replications. A single
cell failing fails G4. The previous confirmation's G3 passed at one budget and
was withdrawn for exactly that; the rule that came out of it is applied here.

`seen_centre` is reported under the same statistics and is not part of the
gate.

## 5. What a pass would mean

That an acquired metric over behaviour transfers to a region of the hypothesis
space that training was never centred on, beating both the free procedure with
the same present evidence and the same metric with its dimensions permuted.

It would not mean the earlier holdout was wrong to fail. It would mean the
boundary that failed four times was a syntactic one with no behavioural
signature, and that when the latent structure of a world is expressible over
something an unseen atom also has, the transfer that kept failing succeeds.

It is one environment, one task form, one descriptor, and one family of latent
structures. No forecast is scored. Nothing here is a claim about the earlier
worlds, whose verdict stands.

## 6. Accounting

The run records wall time, CPU time, peak resident memory, the fitted-to-true
weight correlation, the catalog digest, the runner's SHA-256, and a decision
journal. `audit_metric_world_transfer.py` recomputes every reported rate and
the gate from the journal alone, checks that every recorded pick reproduces the
visible examples, and runs sampled picks through the host interpreter in the
direction grading is sound in.
