# Recursive child-improver growth: tested, failed, and screened

2026-09-21. Development on opened cached panels.
Sources: `analysis/recursive-improver-development-20260921.json`,
`analysis/scheme-choice-regret-20260921.json`.

## The test

Improver growth is established: more verified history builds a better system.
Recursive growth is the stronger claim the measurement contract has always
listed as unmet. It asks whether a later parent improves the *process* it hands
on, not the artifact it builds.

Design, with the child's data held fixed so only the inherited process varies:

- Each parent holds its own history and selects a **partition scheme** from a
  catalog by leave-a-block-out cross-validation on that history. The scheme is
  its entire transmissible state: no model, no router, no labels.
- Every child receives one scheme, an **identical fresh history of 12 banks that
  no parent saw**, and builds its own partition, specialists and router on it.
- Children are scored on an untouched transfer panel.

## Result: failed

The parents genuinely disagreed, so the test was not vacuous. The early parent
(4 banks) selected `flat`; the late parent (32 banks) selected `coarse`, with
its own cross-validation ranking coarse 922, finest 907, fine 904, default 899,
flat 832.

The children were indistinguishable.

| child | inherited scheme | total |
| --- | --- | --- |
| early parent's | flat | 366 |
| **late parent's** | coarse | **364** |
| default scheme, no parent needed | default | 366 |
| scrambled | finest | 362 |

**G3 recursive growth: -2**, four winning and seven losing banks, interval -15 to
+12. **G3b against the default scheme: -2**, interval -18 to +13.

## Why: the transmissible state fails P2c

The precondition screen should have been run before the experiment, and was not.
Running it afterwards explains the null completely. Scoring every scheme directly
at each child history size:

| child history | flat | coarse | default | fine | finest | oracle | default regret |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 326 | 325 | 325 | 325 | 325 | 326 | **+1** |
| 6 | 332 | 340 | 329 | 340 | 335 | 340 | **+11** |
| 12 | 344 | 359 | 357 | 352 | 349 | 359 | **+2** |
| 24 | 355 | 376 | 368 | 379 | 381 | 381 | **+13** |

Every value is below the +20 threshold. A parent transmitting a scheme cannot
buy more than +1 to +13 even with perfect knowledge, and bank noise is of that
size.

The best scheme does shift with data size, finer partitions paying off as
history grows, so a size-adaptive rule was checked as a richer transmissible
state. Summed across the four sizes, the size-adaptive oracle scores 1406
against 1400 for the best fixed scheme, "always coarse": **+6 in total**. That
also fails.

## What this does and does not say

It does **not** say recursive growth is impossible here. It says that *partition
scheme*, the most natural transmissible state in this construction improver, is
worth too little for any parent to demonstrate growth through it. The same
diagnosis retired nine action spaces before the complexity partition succeeded,
and the fix each time was to find a state where no free default already captures
the value.

The methodological lesson is the sharper one: **P2c and P2d must be screened on
the transmissible state before a recursive experiment is run, exactly as they are
for an action space.** This experiment was built and executed first, and the
screen afterwards explained the null in one table at a fraction of the cost.

## The three candidate states, screened

All three were screened after the scheme failure, before any machinery was built
for them. All three fail P2c.

**Regime boundaries.** A rule for *when* to partition needs partitioning to be
harmful somewhere. In both frozen confirmations built is at or above pooled at
every history size (gaps +3, +8, +20, +29 and +7, +14, +37, +26), so
"always partition" is never wrong and the rule transmits nothing.

**Failure memory.** Warning a child off a bad construction needs the bad
construction to cost something. The scheme screen above shows every
alternative within +1 to +13 of the default, so there is nothing worth
remembering.

**Acquisition policy.** Which history banks are worth acquiring, screened on the
audited replication-one banks (`analysis/acquisition-regret-screen-20260921.json`):

| budget K | best free rule | top-K by leave-one-out value | regret |
| --- | --- | --- | --- |
| 4 | arrival order, 321 | 300 | **-21**, interval -38 to -4 |
| 8 | widest spread, 327 | 323 | **-4**, interval -19 to +10 |

At K=8, nine selection rules, including eight averaged random draws, three
public heuristics and two labelled ones, all score between 320 and 327. The
subset a child acquires is worth about seven points. Top-K by leave-one-out
marginal value is not a true best-subset oracle, so that reference is weak; the
rejection stands because nothing beats the trivial default by more than +6.

**Conclusion: no practically sufficient recursive advantage was found in the
three tested transmission classes, at the tested budgets, under the accuracy
endpoint.** This is not a proof of exhaustion. An inherited procedure that
reached the same accuracy at lower construction cost would not register on this
endpoint, and the tested states do not span reusable representations, optimizer
state or search heuristics. This is the same shape as the nine failed
action spaces before the complexity partition succeeded, one level up: every
process-level choice a parent could hand on is already made well enough by a
free default. Finding a state that is not would require an environment change,
not a better parent.

## What a qualifying transmissible state needs

It must carry information that a researcher's free default does not already
encode, and that the child cannot recover from its own data. Candidates, none
tested:

- **Acquisition policy**: which tasks are worth labelling, where the child
  cannot know the answer before paying.
- **Failure memory**: specific constructions that were tried and harmed, which
  the child would otherwise repeat at its own cost.
- **Regime boundaries**: where a construction stops working, learnable only from
  histories spanning a boundary the child's data does not cross.

Each is screenable for default regret before any recursive machinery is built.

## Limits

- Opened cached panels; development evidence only.
- One child history and one transfer panel, so a single draw rather than a
  replication. The null is unambiguous enough that replication was not the
  binding issue; the regret screen was.
- The scheme catalog is researcher written; the parent chooses within it rather
  than inventing schemes.
- Regret figures use the transfer panel and are therefore upper bounds on what
  any parent could transmit.
