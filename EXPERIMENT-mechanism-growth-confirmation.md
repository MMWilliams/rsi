# Predeclaration: confirmatory run on drawn mechanisms and worlds

Written 2026-09-21, before the confirmatory seeds are drawn. Development
evidence is in `analysis/mechanism-*-20260921.json` and is summarised in
`MECHANISM-GROWTH-RESULTS-2026-09-21.md`. Every threshold, arm, split and
statistic below is fixed here; the run that follows reports them whether they
pass or fail.

## 1. What is being tested, and against what

The environment is `rsi/mechanism_space.py`. A mechanism is one of 166,596
behaviourally distinct character predicates written in the host interpreter's
ordinal expression language. A *world* admits about 150 of them, namely those
built only from its 14 atom keys, and nothing in a task reveals which. A task
shows eight examples of a mechanism and hides sixteen. An arm orders the
catalog, scans the first `B` entries, keeps what is consistent with the visible
examples and picks among those by a fixed free rule (smallest positive set,
then lowest complexity). Ordering is therefore the only thing any comparison
here is about, and `B` is the only resource.

Three claims, in increasing order of how far the holdout reaches. Each is
measured against the best experience-free rule available at the same budget and
the same number of solved mechanisms, because the standing rule in this
repository is that a built system must beat the free procedure in its class,
and every improver claim that ignored one has been withdrawn.

## 2. Arms

Experience-free, no solved mechanisms used:

- `complexity` catalog order, lowest complexity first.
- `density` density closest to one half.

Experience of the world at hand, `k` solved mechanisms disjoint from the tested
ones:

- `free_count` atoms weighted by how often they appear in those `k`.
- `free_set` the same atoms treated as a set. Stronger than `free_count` in
  development and therefore the reference for the transfer claims.

Experience of 400 other worlds, observed only through 64 solved mechanisms
each, on top of the same `k`:

- `meta_identity` affinity between atom identities, estimated by counting how
  often two atoms appear in one world, never allowed to score an atom below
  what the present world has shown.
- `meta_metric` a diagonal metric over whitened Fourier and Walsh magnitude
  spectra of atom masks, fitted to world co-membership on the training worlds.
  Defined for atoms no training world contained.
- `meta_both` the higher of the two.

Controls:

- `wrong_world` the within-world rule fed a different world's solved set.
- `meta_uniform` the identity affinity fitted on worlds drawn with no family
  structure.
- `meta_identity_scrambled` the affinity matrix with atom labels permuted.
- `meta_metric_scrambled` the metric fitted on descriptions permuted across
  atoms.

## 3. Splits

Training worlds are drawn from three-family combinations that exclude two
withheld families and six withheld combinations. Evaluation worlds:

- `seen_triple` a family combination the training worlds used.
- `new_triple` families each trained on, never in this combination.
- `new_family` at least one family no training world contained.

Test mechanisms of evaluation worlds are removed from every training world's
solved sample, so no mechanism tested was ever observed, in any world.

## 4. Predeclared criteria

Two replications with independent seeds, 16 worlds per split, 40 test
mechanisms per world, so 640 tasks per split per replication. Paired bootstrap
over tasks, 20,000 resamples. A claim passes only if it passes in **both**
replications.

**G1, within-world growth.** At budget 256, `free_set:32` minus the better of
`complexity` and `density`, summed over the 1,920 tasks of a replication, is at
least **+400** with a bootstrap interval entirely positive; and `free_set:32`
minus `wrong_world:32` is at least **+400** on the same tasks with an interval
entirely positive.

**G2, transfer to an unfamiliar world.** On `new_triple`, at k in {1, 2, 4} and
budget 1024, `meta_identity` minus the better of `free_count` and `free_set` is
at least **+20** of 640 with an interval entirely positive at every one of the
three k, and `meta_identity` minus each of `meta_uniform` and
`meta_identity_scrambled` is positive with an interval entirely positive at
every one of the three k.

**G3, transfer to an unfamiliar family.** On `new_family`, at k in {2, 4} and
budget 1024, `meta_metric` minus the better free rule is at least **+20** of 640
with an interval entirely positive at both k, and `meta_metric` minus
`meta_metric_scrambled` is positive with an interval entirely positive at both
k. Development evidence for G3 was inconsistent across budgets and it is
expected to be the criterion that fails; it is declared so that the failure is
a result rather than an omission.

Budgets reported: 256, 1024, 4096, 16384, and the full catalog. k reported:
1, 2, 4, 8, 16, 32. Criteria are read only at the budgets and k named above.

## 5. What a pass would and would not mean

A pass on G1 is growth in the weakest sense the adopted definition allows:
unfamiliar problems, controlled resources, and a control showing the gain is
specific to the structure acquired. It is one environment and one task form.

A pass on G2 is the first result in this repository where experience of some
mechanisms improves the acquisition of mechanisms that were never seen, in
worlds that were never seen, against a free rule with the same present
evidence. It would still be bounded by G3: a family no training world
contained is outside it.

Neither is a claim about improvement productivity, recursive growth or
compounding growth. No forecast is scored here. Nothing here licenses a claim
about any other environment.

## 6. Accounting

The run records wall time, CPU time, peak resident memory, the count of tasks
with no consistent candidate, the catalog digest and the SHA-256 of the runner.
An independent audit (`audit_mechanism_growth_confirmation.py`) recomputes a
random sample of decisions from the stored task bank, re-deriving each chosen
candidate's correctness through the host interpreter `evaluate_program` rather
than the mask test the runner uses, and recomputes every reported total from
the stored decision records.
