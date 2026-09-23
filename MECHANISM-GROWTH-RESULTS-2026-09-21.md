# Growth measured on drawn mechanisms and drawn worlds

Built and run 2026-09-21, after the day's three reviews left no growth claim
standing (`WHAT-WORKED-WHAT-FAILED-2026-09-21.md`). The verifier claim died on
a mechanism holdout: an evaluator trained on five of six hand-written families
was worse than the base evaluator on the sixth, on every one of them. The
diagnosis in that document is that "unfamiliar" in this repository had only
ever meant a new seed of a familiar generator, and that a learning-ability
claim needs mechanisms that are drawn rather than chosen.

This is the environment that draws them, and the measurements made on it. Two
claims pass a predeclared confirmation on independent seeds and an independent
audit. One passes as written and should not be believed, for a reason recorded
in §4. Beyond the confirmation, §5 is the first compounding curve this
repository has produced, §6 charges the experience to the agent that benefits
from it, which is the accounting every earlier claim here was missing, and §7
explains the one boundary nothing has crossed, rebuilds the question so it is
answerable, and reports three further predeclared confirmations, all of which
failed.

## 1. The environment

`rsi/mechanism_space.py`. A mechanism is a character predicate written in the
host interpreter's own ordinal expression language, so the interpreter, not the
generator, decides what a predicate means. Enumerating every atom, every
cross-family pair under three boolean operators and every complement, and
keeping one representative per distinct truth mask over a 256 character
alphabet, gives a catalog of **166,596 behaviourally distinct predicates**, of
which 105,126 are balanced enough to generate tasks.

A task shows eight examples of one mechanism and hides sixteen. An example is
2-5 characters satisfying the predicate followed by 2-5 that do not; the answer
is the first block. The alphabet is `chr(0x800 + i)`, all Unicode category Lo,
so the interpreter's built-in letter/digit transition carries no signal and the
predicate has to be invented.

A **world** admits the roughly 150 catalog entries built only from its 14 atom
keys, drawn from three atom families. Nothing in a task reveals them.

Four properties are what make the measurements below mean anything:

- **The truth is in the hypothesis space.** An unsolved task is a failure of
  inductive bias or of budget, never of coverage.
- **There is no max-over-noisy-labels oracle.** Correctness is the interpreter
  running a program on held-out examples.
- **Unfamiliarity is graded and drawn.** New strings, new catalog entry, new
  key set, new family combination, new family: five different questions, never
  merged.
- **Resources are countable.** An arm orders the catalog, scans the first `B`
  entries, keeps what is consistent with the visible examples and picks among
  those by one fixed free rule. Ordering is the only thing that differs between
  arms and `B` is the only resource, so "one larger budget" is always available
  as a default.

`tests/test_mechanism_space.py` checks the load-bearing invariant directly: for
sampled tasks and candidates, the two integer mask tests the experiments use
agree with `evaluate_program` on the rendered program, candidate by candidate.
Thirteen tests pass.

## 2. What the screens said before anything was built

**Power (P2).** `analysis/mechanism-screen-20260921.json`, run on an earlier
build of the catalog (157,878 rows, before every cross-family pair was
enumerated and before worlds existed; the script is marked superseded and does
not import against the current module). Eight examples left 17.2 consistent
candidates on average and a unique one 39.3% of the time. At unlimited budget,
Occam ordering solved 0.645 and the *generator's own weight function*, which
was the exact Bayes ordering and known to no arm, solved 0.648. **There was no
headroom in selection.** The residual was reachability: at a budget of 16,384
of 157,878 the same orderings solved 0.063 to 0.130. That build had an explicit
weight function over the catalog, which the current one does not, so this
particular ceiling is not reproducible from the present code.

**Learnability (P2d) in selection**, re-established on the catalog everything
else here uses. `mechanism_selection_recheck.py`, 4,000 drawn mechanisms,
166,596 rows: eight examples leave 8.6 consistent candidates on average, a
unique one 41.9% of the time, and some consistent candidate is correct on every
task. Given the whole consistent set at unlimited budget:

| | mechanism holdout | family holdout |
| --- | --- | --- |
| fitted selector, 60 leaves | 0.785 | 0.825 |
| smallest consistent set | **0.787** | **0.830** |
| largest agreement with the rest | **0.788** | 0.825 |
| lowest complexity | 0.756 | 0.787 |
| random consistent candidate | 0.651 | 0.715 |

**Fitting adds nothing over a free rule**, under a mechanism holdout and under
a family holdout, on both catalog builds. Sixty seconds of compute, and the
same shape as the result that took the previous programme two days.

Everything after this measures reaching a good hypothesis, not choosing among
the ones already in hand.

## 3. Development sequence

| run | finding |
| --- | --- |
| `mechanism-world-growth` | Within a world, experience of its own mechanisms takes the solve rate at budget 256 from 0.008 (best free order) to 0.803 at 64 solved mechanisms; the same rule fed another world's mechanisms stays at 0.000 |
| `mechanism-meta-growth` | Experience of 400 *other* worlds lifts a world with an unfamiliar family combination from 0.135 to 0.535 at one solved mechanism and budget 1024, controls at baseline; on a world containing an untrained family the same prior falls **below having no prior**, to 0.077 against 0.056-0.706 |
| `mechanism-meta-support` | The cause is in the estimator, not the environment: an atom absent from training has zero affinity everywhere, so an atom the agent had just watched solve a task *in this very world* was assigned zero probability. Prior experience was overruling present evidence |
| `mechanism-meta-transfer` | Repaired, and measured against the stronger free rule (atoms as a set, not weighted by count): transfer holds on unfamiliar family combinations, and on an untrained family it is positive at tight budgets and negative at loose ones |
| `mechanism-family-transfer` | A prior over Fourier and Walsh magnitude spectra of atom masks, which exist for atoms never seen, removes the collapse; but the same descriptions permuted across atoms do as well, so that arm was reading the shape of a soft prior, not the behaviour of the atoms |
| `mechanism-metric-transfer` | A metric over those spectra, fitted to world co-membership on the training worlds, beats the permuted control at several budgets and k, inconsistently |

Two methodological corrections came out of this sequence and are now permanent:

- **Tie-breaking by catalog order gave the free rules a systematic preference
  among rows they cannot tell apart**, and made their solve rate jump between
  budgets for reasons unrelated to their scores. Every arm now shares one
  random tie-break (`Harness.set_tiebreak`).
- **The free rule must be the best free rule.** Weighting atoms by how often
  they appear in the solved set is worse than treating them as a set, and an
  early version of the repaired prior was credited with a gain that was really
  this flattening. `free_set` is the reference for every transfer claim.

## 4. The confirmation

`EXPERIMENT-mechanism-growth-confirmation.md` predeclared the arms, splits,
budgets, statistics and thresholds. `mechanism_growth_confirmation.py` ran two
replications on seeds 921001 and 921002: 16 worlds per split, 40 test
mechanisms per world, 640 tasks per split, 1,920 per replication, no task
without a consistent candidate. Test mechanisms are removed from every training
world's solved sample, so no tested mechanism was observed in any world. Paired
bootstrap over tasks, 20,000 resamples. Cost: 220 s wall, 254 s CPU, 192 MB
peak, both replications.

### G1, within-world growth: passed

At budget 256, over the 1,920 tasks of a replication:

| replication | experience(32) minus best experience-free order | minus the same rule on another world's mechanisms |
| --- | --- | --- |
| 1 | **+1601** | **+1643** |
| 2 | **+1603** | **+1644** |

Rates at budget 256 run 0.034-0.048 for catalog order, 0.003-0.009 for density
order, 0.005-0.052 for another world's experience, and 0.852-0.902 for the
world's own. The development curve is monotone in experience: 0.001, 0.018,
0.057, 0.165, 0.326, 0.644, 0.775, 0.803 at 0 to 64 solved mechanisms.

Acquiring a world's structure is worth more than any amount of the budget: at
64 solved mechanisms and a budget of 256, experience beats every free order
*at unlimited budget*, because the ordering also puts good hypotheses ahead of
bad ones among those it does reach.

### G2, transfer to an unfamiliar world: passed

On `new_triple`, worlds whose three families were each trained on but never in
this combination, at budget 1024, tasks out of 640:

| k | minus best free rule | minus no-structure control | minus label-scrambled control |
| --- | --- | --- | --- |
| 1 | +127 [103, 150] / +127 [102, 152] | +110 [86, 134] / +127 [102, 152] | +119 [95, 142] / +128 [103, 153] |
| 2 | +190 [163, 217] / +188 [163, 214] | +176 [152, 200] / +185 [161, 210] | +191 [167, 215] / +166 [141, 191] |
| 4 | +204 [178, 230] / +201 [174, 227] | +219 [193, 245] / +189 [162, 216] | +214 [189, 239] / +170 [144, 196] |

Both replications, every comparison, every interval entirely positive, and the
same sign at every budget from 256 to 16,384. In sample-efficiency terms, at
budget 1024 on `new_triple`, one solved mechanism plus experience of 400 other
worlds reaches 0.331 and 0.338, which the free rule needs **four to five**
solved mechanisms of the new world to match.

The mechanism is legible. A world takes 14 keys from three families, so atoms
of one family co-occur across training worlds. The prior therefore generalizes
from an observed atom to the atoms that travelled with it, which is why it
reaches a family combination it never saw, and why §5 is what it is.

### G3, transfer to an unfamiliar family: passed as written, not established

On `new_family`, worlds containing a family no training world held, the fitted
spectral metric minus the best free rule at budget 1024 is +35 [12, 58] and
+22 [2, 42] in replication 1 at k of 2 and 4, and +33 [13, 53] and +23 [4, 42]
in replication 2, with the permuted-description control beaten in all four
cells. That is what the protocol asked for, and it passes.

It should not be believed, because the protocol asked the wrong question. The
same comparison at other budgets, same runs:

| budget | k=1 | k=2 | k=4 | k=8 |
| --- | --- | --- | --- | --- |
| 256 | +13 / +13 | +29 / +12 | **-16 / -17** | **-18 / -52** |
| 1024 | +7 / -5 | +35 / +33 | +22 / +23 | +22 / +7 |
| 4096 | **-46 / -63** | **-41 / -39** | -10 / +3 | +21 / +42 |
| 16384 | +46 / +57 | +29 / -1 | -17 / -8 | -26 / -9 |

Bold cells have intervals entirely negative. A gain confined to one budget,
with significant losses on either side of it, is a budget-specific artifact
and not transfer. Reading the gate at a single budget was a flaw in the
predeclaration, chosen because 1024 was where development evidence looked
best; that is selection, even when declared in advance. **Future gates in this
environment must require the same sign across the whole reported budget range,
not at one point.**

The honest statement is the one from §5: an identity prior generalizes from an
atom to atoms that co-occurred with it, and has nothing to say about an atom it
never saw. Describing atoms by behaviour makes them describable; it has not yet
been shown to make them predictable.

### What the audit found

`audit_mechanism_growth_confirmation.py` rebuilds the constraint masks from the
recorded strings, recomputes every rate and every gate from the decision
journals alone, rebuilds the experience-free ordering and repeats the scan for
3,840 sampled decisions, and runs 31,336 sampled picks through
`evaluate_program`. **It passes.** Every rate and every gate recomputed to the
value reported; all 3,840 rebuilt picks matched the recorded ones exactly; no
pick was inconsistent with its visible examples; no tested mechanism appeared
in the experience pool used to choose for it.

Its first pass failed, on 14 of 2,741 interpreter checks
(`analysis/audit-mechanism-growth-confirmation-20260921-first-pass.json`). The
cause is a real property of the grading rule and is now stated in the
environment. Grading reads a predicate as *the longest satisfying prefix*; the
rendered program's interpreter reading is *up to the end of the first run*,
which also accepts a run beginning after position zero. A direct count over
75,063 sampled decisions found the disagreement is entirely one-directional:
**0 cases where grading credited an answer the interpreter rejects, 105 where
the interpreter accepts an answer grading counts as a miss**, a rate of 0.14%.
Grading is therefore sound and slightly conservative, uniformly across arms,
and the true mechanism always satisfies the prefix reading so no task is made
unsolvable. The margins in G1 and G2 are 24 and 20 to 32 percentage points and
cannot turn on 0.14%; G3's margin is 3.4 points and is withdrawn on other
grounds. The audit now checks the sound direction and measures the permissive
one.

## 5. Compounding: does the ability to acquire improve with worlds seen?

G2 is a level, not a derivative: a fixed amount of prior experience buying a
fixed advantage. `mechanism_compounding.py` fits the same estimator on the
first 25, 50, 100, 200 and 400 training worlds and reads the margin over the
free rule on 20 worlds whose family combination no training world used, 800
tasks. The control is the identical sweep on worlds drawn without family
structure, where there is nothing to accumulate.

Margin over the free rule, tasks of 800:

| k | budget | 25 | 50 | 100 | 200 | 400 | 400, unstructured |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1024 | -26 | -7 | +20 | +37 | **+54** [29, 80] | -4 [-26, 18] |
| 2 | 1024 | +21 | +60 | +79 | +90 | **+122** [94, 150] | -14 [-37, 8] |
| 4 | 1024 | +20 | +47 | +55 | +94 | **+104** [77, 131] | -20 [-41, 1] |
| 1 | 4096 | -95 | -96 | -67 | -35 | +5 [-19, 29] | -64 [-82, -47] |
| 2 | 4096 | -146 | -101 | -47 | -10 | **+43** [19, 67] | +10 [-8, 28] |
| 4 | 4096 | -77 | -20 | +33 | +80 | **+102** [73, 131] | -35 [-64, -7] |

The structured curve is monotone in all six rows and has not flattened at 400
worlds. The unstructured sweep is flat or negative everywhere and never
becomes monotone, so this is structure accumulating and not an estimator
warming up. At k=2 and budget 1024 the solve rate runs 0.182 for the free rule,
0.209 at 25 worlds, 0.281 at 100, 0.335 at 400, and 0.165 for the unstructured
prior at 400.

Two things this is not. It is not recursive: the estimator that turns worlds
into a prior is fixed, and only its input grows. And the small-sample cells are
a warning rather than noise: at budget 4096 a prior fitted on 25 worlds is
worse than no prior by -95 to -146 with intervals entirely negative. **A weak
acquired prior is worse than none**, which is the same disease as §4's
identity collapse in a milder form.

## 6. Earned experience: does the loop close under a charged budget?

Everything above hands an arm its solved mechanisms. Solving them cost budget
and none of it was charged, so §4 and §5 measure the value of accumulated
experience, not improvement productivity. `mechanism_lifelong.py` charges it.
An agent meets 120 tasks from one world, each a mechanism it has never seen,
spends the same scan budget on every one, and starts knowing nothing. Whatever
it learns comes from tasks it has already paid for, so the total resource is
identical for every arm: 24 worlds, one shared task stream per world, paired.

Tasks solved of 120, mean over worlds, with the solve rate in the first ten
tasks and the last ten:

| arm | budget 256 | first 10 → last 10 | budget 1024 | first 10 → last 10 |
| --- | --- | --- | --- | --- |
| static, never updates | 0.8 | 0.008 → 0.013 | 1.8 | 0.021 → 0.013 |
| blind, keeps what it submitted | **3.5** | 0.013 → 0.037 | **19.7** | 0.037 → **0.292** |
| feedback, keeps it when told it was right | 2.4 | 0.013 → 0.017 | 17.2 | 0.042 → 0.287 |
| feedback plus the cross-world prior | 3.8 | 0.008 → 0.054 | 20.8 | 0.033 → 0.325 |
| told the true mechanism every time | 95.6 | 0.250 → 0.883 | 99.0 | 0.300 → **0.925** |

Against the arm that never updates: blind +429 [289, 576] and feedback
+371 [255, 493] at budget 1024, +66 [28, 112] and +40 [12, 72] at 256, over 24
worlds.

Three things follow.

**The loop closes, and it closes without feedback.** The `blind` arm consults
nothing outside the task: it keeps the atoms of whatever it submitted, right or
wrong, and its solve rate rises eightfold across its own stream at a fixed
per-task budget. Every candidate it submits was consistent with eight examples,
which is apparently enough for the atoms to be worth keeping even when the
answer was wrong. It is also, at both budgets, at least as good as the arm that
is told whether it was right, so the one bit of outcome feedback buys nothing
here.

**There is no takeoff threshold; there is a fraction of the ceiling that grows
with the resource.** Two budget points suggested a threshold and six do not.
`mechanism_takeoff.py`, 16 worlds of 100 tasks:

| budget | never updates | blind | told the mechanism | blind, first 20 → last 20 | blind minus static |
| --- | --- | --- | --- | --- | --- |
| 128 | 0.2 | 1.8 | 48.5 | 0.003 → 0.031 | +25 [4, 51] |
| 256 | 0.5 | 4.9 | 78.5 | 0.013 → 0.091 | +71 [19, 144] |
| 512 | 0.7 | 8.7 | 82.2 | 0.022 → 0.172 | +128 [69, 199] |
| 1024 | 1.3 | 13.3 | 80.6 | 0.044 → 0.219 | +192 [118, 280] |
| 2048 | 1.8 | 28.2 | 79.4 | 0.084 → 0.447 | +422 [299, 544] |
| 4096 | 3.4 | 53.2 | 78.1 | 0.200 → 0.772 | +796 [730, 858] |

The loop closes at every budget tested, with an interval entirely positive at
every one, and the last-twenty rate is 4 to 10 times the first-twenty rate
throughout. What changes with the budget is how much of the informed ceiling
the earned loop recovers: **3.7%, 6.2%, 10.6%, 16.5%, 35.5%, 68.1%**. The
ceiling itself saturates by budget 256, because an agent told the true
mechanism knows its world's 14 atoms within a few tasks and 256 entries is
enough to reach what they generate. So the earned agent is not budget-limited
in the same way the informed one is: it is limited by how fast correct atoms
arrive, and the budget only sets the rate.

**The cross-world prior of §4 does not accelerate the loop**: +86 [-40, 222] at
budget 1024 and +34 [-1, 83] at 256, both crossing zero. The prior that is
worth four to five solved mechanisms when those mechanisms are handed over
cannot be shown to be worth anything when the agent must earn them. That is the
difference between the value of experience and improvement productivity,
measured, and it is the reason §4 must not be read as the latter. The next
subsection shows the reason is *when* that prior applies rather than how good
it is, and that a prior which applies before the first solve changes the loop
completely.

The gap to the ceiling is the whole remaining problem: an agent told the true
mechanism each time reaches 0.925 in its last ten tasks against 0.292 earned.
What limits the earned loop is the rate at which correct information arrives,
not the rule that uses it.

### A prior that works before the first solve

The prior confirmed in G2 cannot help the earned loop because of when it
applies, not how good it is: it conditions on the atoms of mechanisms the agent
has already solved, and an agent that has solved nothing has nothing to
condition on. For exactly the stretch that decides whether the loop ever starts,
it is the no-experience ordering.

What the training worlds also know, and that prior never used, is which *pairs*
of atoms belong together in any world at all. That is unconditional, available
before the agent sees a single task, and not expressible as a score on each
atom separately. `mechanism_cold_start.py` starts the earned agent from that
ordering and otherwise changes nothing. Training worlds use seven atom
families; half the evaluation worlds use only those and half contain one of the
two families no training world held. Tasks solved of 100, 16 worlds per group:

| group | budget | static | blind | **warm** | warm, atom rates only | warm, labels permuted | ceiling |
| --- | --- | --- | --- | --- | --- | --- | --- |
| familiar families | 256 | 0.6 | 3.4 | **23.0** | 19.5 | 3.9 | 84.6 |
| familiar families | 1024 | 1.9 | 13.6 | **52.4** | 49.1 | 17.6 | 83.4 |
| unfamiliar family | 256 | 0.3 | 2.3 | 7.2 | 7.1 | 5.4 | 81.2 |
| unfamiliar family | 1024 | 1.3 | 13.7 | 10.7 | 9.5 | **19.9** | 81.4 |

On familiar families the cold-start prior is worth more than everything else in
this document put together: **+314 [193, 432]** over the earned-loop champion at
budget 256 and **+621 [384, 841]** at 1024, with the permuted control beaten by
+306 [212, 396] and +558 [350, 763]. It takes the share of the informed ceiling
the earned agent recovers from 4% to 27% at budget 256, and from 16% to 63% at
1024. Most of that is knowing which atoms appear in worlds at all rather than
which pairs go together: replacing pair co-occurrence with each atom's own rate
loses only +56 [17, 102] at 256 and +53 [-5, 106] at 1024.

On a family no training world held, the same prior is **worse than the
permuted control**, -147 [-240, -60] at budget 1024, and cannot be
distinguished from it at 256 (+28 [-27, 83]). Third independent demonstration
of the same boundary, now in the earned loop: what is acquired from other
worlds is support, and outside that support it is a liability.

One limit of this run: mechanisms used in the evaluation streams were reserved
from the training worlds' solved samples by index order rather than by the
shuffled stream, so the reservation is incomplete. The prior is a function of
atom keys alone and carries no mechanism-level information, so this cannot
transmit an answer; it is recorded rather than repaired.

### Bounding the loss: the hedge works, the detector does not fire

Every acquired prior in this line of work has failed in one place and no other:
outside the support of what it was trained on. `mechanism_hedged_start.py`
tests the two repairs that place admits. **Hedge**: reserve a fixed share of the
scan budget for the order the agent would use with no prior at all, which needs
nothing to be detectable because the loss is bounded by the reserved share
whatever the prior believes. **Detect**: switch the prior off once the fraction
of the agent's own solved atoms that appear in no training world exceeds the
share a hedge would have reserved. Tasks solved of 100, 16 worlds per group,
against the earned loop with no prior:

| group | budget | prior | hedge 25% | hedge 50% | detector |
| --- | --- | --- | --- | --- | --- |
| familiar families | 256 | +274 [176, 412] | +263 [170, 389] | +235 [164, 327] | +274 [176, 412] |
| familiar families | 1024 | +298 [134, 507] | +301 [158, 496] | **+325 [186, 515]** | +298 [134, 507] |
| unfamiliar family | 256 | +95 [46, 146] | +98 [50, 147] | +87 [46, 130] | +95 [46, 146] |
| unfamiliar family | 1024 | **-5 [-93, 76]** | +65 [-32, 165] | **+121 [26, 213]** | -5 [-93, 76] |

Absolute counts move a long way between runs of this kind: the no-prior arm
solves 3.4 of 100 in the cold-start run and 0.9 here at budget 256, on
different world draws and a different tie-break, with sixteen worlds each.
Every comparison reported is paired within its own run and the differences
reproduce; the levels should not be read across runs.

The hedge converts the failure into a gain. At budget 1024 on a family no
training world held, the unhedged prior is worth nothing and reserving half the
budget is worth +121 with an interval entirely positive; in support the same
reservation costs nothing at 1024 and about a seventh of the gain at 256. It
buys the one guarantee this project has never had from an acquired prior: a
bound on how badly it can go wrong where it does not apply.

**The detector never fired**, in any group, at any budget: its arm is identical
to the unhedged prior in every cell. Foreign atoms picked up from wrong answers
come mostly from the families training did contain, so the fraction of unseen
atoms among what the agent knows stays below the threshold even in a world
whose third family was withheld. The statistic is not wrong but it is diluted,
and the hedge needs no statistic at all. Use the hedge.

### The obvious estimator upgrade does not work

The confirmed prior scores an atom by its strongest *pairwise* affinity to an
atom already solved, which looks like a crude reading of training worlds that
are sets. `mechanism_world_retrieval.py` replaces it with the direct question:
weight each training world by how many of the solved atoms it contains, with an
exponential penalty per atom missed, and average the worlds' own atom sets, over
a uniform floor so a world resembling nothing in training degrades to the free
rule. On a third independent seed it reproduces G2 (pairwise affinity minus the
free rule, +106 to +194 of 640 at budget 1024 on `new_triple`), and the upgrade
loses: retrieval minus affinity is **-43, -54, -39, -22** and similar across
`seen_triple` and `new_triple`, with intervals entirely negative in most cells
and never reliably positive.

It is not that retrieval ignores the worlds: retrieval minus the same
estimator with every world weighted equally is +9 to +66. It is that weighting
concentrates the estimate on the handful of training worlds that happen to
contain one to four observed atoms, and a maximum over pairwise counts pools
the same evidence across every world containing that atom. At the evidence
levels where a prior is worth having, the cruder summary is the more robust
one.

### A defect found in a reported arm

`meta_both`, declared as the higher of the identity and metric scores, is
identical to `meta_metric` in every cell of both replications. The metric is a
logistic probability fitted on pairs balanced one to two, so its outputs sit an
order of magnitude above the identity affinities and the maximum is always the
metric. The two scores are not on a common scale and the arm is uninformative.
It is withdrawn; no claim rests on it.

## 7. The boundary, explained and then re-tested

Four attempts to reach a world built from a family no training world contained
had failed: the identity prior by construction, an untrained spectral cosine
because its permuted control matched it, a fitted spectral metric
inconsistently across budgets, and the hedge by bounding the loss without
creating a gain. The fifth measurement explains the other four.

**The boundary was syntactic.** `mechanism_atom_clustering.py` clusters the 368
atoms by the whitened Fourier and Walsh magnitude spectra of their masks and
asks how well the clusters recover the nine families. Best agreement over k in
6 to 32 is **adjusted Rand 0.144**. Per family at the best k: `threshold` is
recovered perfectly, `parity` 0.86, `bit` and `rotmod` 0.75, and the two
families normally withheld are captured at 0.69 and 0.47 with 0.68 and 0.72 of
their home clusters foreign. This is not a weak descriptor so much as a
category that is not behavioural: in those worlds a family is the *name of an
arithmetic operation*, and `mod:2:0` and `mod:16:7` share a label and nothing
observable. The family holdout asked for generalization across a boundary
nothing computable on an atom can see, and no representation defined on
behaviour could have crossed it. The repeated failure is a fact about how those
worlds were built, not a law about transfer.

**So the question was rebuilt to be answerable.**
`mechanism_metric_worlds.py` draws a sparse random weighting over the 385
descriptor dimensions, shows it to nobody, and defines a world as a centre atom
plus the fourteen atoms nearest it under that weighting. Every atom has a
descriptor, so a prior stated over the weighting is defined for atoms no
training world contained. `EXPERIMENT-metric-world-transfer-confirmation.md`
predeclared G4 on worlds centred on the two withheld families: the fitted
metric must beat the free unweighted proximity rule by at least +15 of 640
**and** beat its own dimension-permuted copy, at k of 1 and 2, at **every**
budget in {256, 1024, 4096, 16384}, in both replications. The weighting was
redrawn per replication, so the method was on test rather than one draw.

**G4 failed, in both replications.** `metric_world_confirmation.py`, seeds
922001 and 922002. What failed is precisely the control clause:

| | budget 256 | 1024 | 4096 | 16384 |
| --- | --- | --- | --- | --- |
| rep 1, minus free rule, k=1 | +30 [14, 46] | +74 [58, 90] | +89 [71, 107] | +40 [27, 53] |
| rep 1, minus permuted copy, k=1 | +40 [23, 57] | +67 [50, 84] | +101 [82, 121] | +17 [4, 31] |
| rep 1, minus permuted copy, k=2 | +28 [15, 42] | +72 [53, 91] | +88 [70, 106] | **+3 [-9, 15]** |
| rep 2, minus permuted copy, k=1 | **+10 [-3, 23]** | +15 [2, 28] | +42 [25, 60] | **-3 [-18, 12]** |
| rep 2, minus permuted copy, k=2 | **+9 [-4, 23]** | +56 [39, 74] | +20 [7, 34] | **+10 [-3, 24]** |

The fitted metric beats the free rule in fifteen of the sixteen gate cells with
intervals entirely positive, and beats a permuted copy of itself in all four
cells at budgets 1024 and 4096 in both replications, and in none of the failing
cells at 256 or 16384. The reading that fits: at 256 the window is so small
that any sparse concentrated weighting picks the same handful of rows, at 16384
it is large enough that both cover the world's region, and the dimensions a
metric actually learned matter only where an ordering has to discriminate
inside a middle-sized window. The fitted-to-true weight correlation was 0.117
and 0.329, so little of the true structure was recovered either way.

Restricting the claim to budgets 1024 and 4096 after seeing this is exactly
what withdrew G3. **G4 is failed and the claim is not made.**

**Then two screens found that G4 had asked for something unidentifiable.**
`mechanism_metric_form.py`: fitting to squared differences, the form a weighted
distance actually takes, rather than to elementwise products, moved recovery of
the true active dimensions from 0.28 to 0.29, so the estimator was not fitted
to the wrong thing. `mechanism_metric_identifiability.py`: the catalog has 368
atoms and the descriptor 385 dimensions, so a weighting over those dimensions
is not determined by the distances among those points. Reducing the descriptor
to its leading principal components, computed from the catalog alone at no
experiential cost, recovers it:

| descriptor width | 8 | 16 | 32 | 64 | 128 | 385 |
| --- | --- | --- | --- | --- | --- | --- |
| active dimensions recalled | 1.00 | 1.00 | **0.92** | 0.90 | 0.70 | 0.33 |
| correlation with the truth | 0.84 | 0.92 | 0.90 | 0.86 | 0.85 | 0.13 |

G4 therefore asked whether an arm could learn something that was not
identifiable from what it was shown, and its failure says nothing about
transfer.

**G5 repeated it with the target identifiable**, at width 32 with 8 active
dimensions, both fixed in
`EXPERIMENT-metric-world-transfer-confirmation-2.md` before any task was run at
that width, everything else unchanged. The weighting was now recovered at
Pearson **0.939** and **0.976**, and the fitted metric beat both the free rule
and its permuted copy in **fifteen of sixteen gate cells in each replication**.
Both replications failed the same one: k=2 at budget 256, margin over the free
rule +10 [-2, 22] and +11 [0, 22] against a floor of +15.

**G5 is failed as predeclared**, and the failing cell is where the protocol
asked for something close to unattainable: in replication 1 the *true*
weighting beats the free rule there by only +19 [3, 35], so a floor of +15
demanded four fifths of all the headroom the cell contains. A floor stated as
an absolute count, applied uniformly to cells with very different headroom, is
a protocol flaw of the same species as G3's single-budget gate. It is recorded
as one rather than repaired after the fact.

**G6 added power at a fixed effect size and nothing else**
(`EXPERIMENT-metric-world-transfer-confirmation-3.md`): 32 worlds per split,
1,280 tasks, floor moved from +15 of 640 to +30 of 1,280, fresh seeds.
Replication 1 **passed every cell**. Replication 2 failed three, and not only
for want of power: at k=2 and budget 256 the permuted copy of the metric beat
the metric itself, -22 [-36, -9], and at k=2 and budget 1024 the margin over
the free rule was +14 [-12, 40].

**G6 is failed.** Three predeclared gates, three failures, and the pattern is
the same in all of them: the effect is large and reproducible at the wider
budgets and unreliable at the tightest. Replication 1 of G6 at k=1 gives
+42, +196, +223, +192 over the free rule across the four budgets and +47, +134,
+173, +169 over the permuted copy; replication 2 gives +46, +72, +224, +70 and
+19, +75, +208, +162. Every cell at budgets 4096 and 16384, in every
replication of G5 and G6, is positive against both comparisons with intervals
entirely positive.

That last sentence is a description, not a claim. A fourth gate restricted to
those budgets would be a range chosen from results already seen, which is what
withdrew G3, and running it would make the whole sequence worthless. **The
claim is not made.** What the environment has established is that the headroom
is real (the true weighting beats the free procedure by up to +168 of 640), that
an identifiable target is recovered almost exactly (Pearson 0.90 to 0.98), and
that converting recovery into a reliable margin at every resource level is not
something a diagonal metric over these descriptors does.

The next study must fix its budget range by a rule stated before it runs and
justified independently of these numbers, for instance "every budget at which
the free procedure solves less than half", together with more worlds. That is
written into `.claude/TODO.md`; it is not run here, because deciding it after
reading three failures is the error this section exists to avoid.

## 8. What is claimed, and what is not

Claimed, in this environment, at matched budget and matched present evidence,
with the structure controls beaten in both replications:

1. Experience of a world's mechanisms improves solving *unfamiliar mechanisms
   of that world*, enormously, and the gain is specific to that world (§4, G1,
   predeclared and audited).
2. Experience of other worlds improves the *acquisition* of a world never seen,
   worth about four to five solved mechanisms of it, and the gain survives an
   unfamiliar combination of families (§4, G2, predeclared and audited).
3. That acquisition advantage keeps growing with the number of worlds
   experienced and has not saturated at 400, while the control with no
   structure to accumulate stays flat (§5, development evidence).
4. With every unit of experience earned under the same charged budget, the loop
   closes and needs no outcome feedback: an agent that keeps the atoms of
   whatever it submitted raises its own solve rate four- to tenfold at every
   budget from 128 to 4096 (§6, development evidence).
5. A prior that applies *before* the agent's first solve, learned from other
   worlds, is worth more than everything else here: +314 [193, 432] and
   +621 [384, 841] over that agent at budgets 256 and 1024, taking the share of
   the informed ceiling it recovers from 4% to 27% and from 16% to 63% (§6,
   development evidence, familiar families only).

Not claimed:

- Anything about a family no training world contained. Four demonstrations
  say the opposite and §7 explains why: that boundary is syntactic and has no
  behavioural signature. On worlds rebuilt so the boundary *is* behavioural,
  the predeclared G4 also failed, on its control clause, in both replications.
- That the *conditional* prior of §4 speeds up the earned loop. It is worth
  four to five solved mechanisms when they are handed over and +86 [-40, 222]
  when they must be earned. Claim 5 is a different object: unconditional, and
  applied before the agent has solved anything.
- Anything recursive. §5 grows the estimator's input; nothing here improves the
  estimator that turns worlds into a prior, and §6's agent runs one fixed rule
  for its whole life.
- Anything about another environment. One task form, one alphabet, one
  hypothesis language.
- Any forecast. None was committed before these runs, as the adopted programme
  requires.

## 9. Design rules this produced

1. **An acquired prior must never overrule present evidence.** The collapse in
   §3 was entirely this: an atom observed solving a task in the world at hand
   was assigned zero probability because training had not seen it. Score every
   hypothesis at least as high as the present evidence alone would.
2. **Hedge every acquired prior.** Reserve a share of the budget for the rule
   the agent would use with no prior at all. Half the budget turned the
   out-of-support failure from nothing into +121 [26, 213] and cost nothing in
   support. It needs no detector, and the detector that was tried alongside it
   never fired.
3. **Generalization reaches exactly as far as the representation it is stated
   over.** An identity prior cannot reach an unseen atom, by construction, not
   by accident. This is the constructive form of the mechanism-holdout rule
   already in `.claude/TODO.md`.
4. **A gate must be read across the resource range, not at a point.** §4's G3
   is the demonstration.
5. **Tie-breaks are part of an arm.** Share one random tie-break across arms or
   the baseline inherits a preference nobody declared.
6. **When a prior applies matters as much as how good it is.** The prior
   confirmed in G2 conditions on what the agent has already solved, so it is
   absent for exactly the stretch that decides whether the loop starts. The
   unconditional form of the same experience was worth an order of magnitude
   more to an agent paying for its own experience.
7. **Charge the experience, or you are measuring a different quantity.** The
   value of accumulated experience and improvement productivity came apart
   here by the whole of the effect: four to five solved mechanisms when handed
   over, nothing measurable when earned.
8. **A cruder estimator can beat a better-specified one at the evidence levels
   that matter.** Joint retrieval over training worlds is the right model and
   loses to a maximum over pairwise counts at one to four observed atoms,
   because weighting concentrates on the few worlds that match.
9. **Do not read a threshold off two points.** The takeoff threshold in the
   first version of §6 was an artifact of having measured two budgets; six
   show a smooth curve and no threshold at all.

## 10. Files

Environment and harness: `rsi/mechanism_space.py`, `rsi/mechanism_worlds.py`,
`tests/test_mechanism_space.py`.

Screens and development runs, each writing one file under `analysis/`:
`mechanism_screen.py` and `mechanism_selection_probe.py` (§2);
`mechanism_world_growth.py`, `mechanism_meta_growth.py`,
`mechanism_meta_support.py`, `mechanism_meta_transfer.py`,
`mechanism_family_transfer.py`, `mechanism_metric_transfer.py` (§3);
`mechanism_selection_recheck.py` (§2, replacing the two superseded screens);
`mechanism_atom_clustering.py` and `mechanism_metric_worlds.py` (§7);
`mechanism_compounding.py` (§5); `mechanism_lifelong.py`,
`mechanism_takeoff.py`, `mechanism_cold_start.py`,
`mechanism_hedged_start.py` and `mechanism_world_retrieval.py` (§6).

Three further confirmations, all failed (§7):
`EXPERIMENT-metric-world-transfer-confirmation{,-2,-3}.md`,
`metric_world_confirmation{,2,3}.py`,
`analysis/metric-world-confirmation{,2,3}-20260921.json`,
`runs/metric-world-confirmation{,2,3}-20260921/decisions-{1,2}.jsonl`.
Screens behind them: `mechanism_metric_form.py`,
`mechanism_metric_identifiability.py`.

Confirmation: `EXPERIMENT-mechanism-growth-confirmation.md`,
`mechanism_growth_confirmation.py`,
`analysis/mechanism-growth-confirmation-20260921.json`,
`runs/mechanism-growth-confirmation-20260921/decisions-{1,2}.jsonl`,
`audit_mechanism_growth_confirmation.py`,
`analysis/audit-mechanism-growth-confirmation-20260921.json`.
