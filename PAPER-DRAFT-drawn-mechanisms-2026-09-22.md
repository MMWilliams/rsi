# Drawn mechanisms: measuring growth in the ability to acquire unfamiliar skills

First draft, 2026-09-22. Author list and venue open. Every number is read from
an audited run or from a named analysis file; nothing is quoted from memory.

## Abstract

Claims that a system's ability to learn has improved are usually evaluated on
fresh instances of a fixed set of task generators. That establishes
instance-level transfer and nothing more, and it is compatible with the system
having become more familiar with those generators rather than better at
learning. We introduce a benchmark in which a task's mechanism, the latent
structure that mechanism is drawn from, and that structure's family are all
sampled, so instance, mechanism, world and family holdouts are four distinct
measurements that cannot be substituted for one another. The hypothesis space
is a catalog of 166,596 behaviourally distinct character predicates in a
program-synthesis DSL. The truth is always inside it, so correctness is decided
by the host interpreter rather than by a maximum over noisy labels, and the
resource is an exact count of hypotheses examined.

On this benchmark we confirm, under thresholds fixed before the seeds were
drawn and checked by an independent audit, that experience of a latent
structure improves the solving of unfamiliar mechanisms drawn from it
(+1601 and +1603 tasks of 1,920 over the best experience-free ordering, with a
wrong-structure control at baseline), and that experience of 400 other
structures improves the acquisition of one never seen (+127 to +204 of 640 at
every budget, worth four to five solved mechanisms of the new structure).

We then charge the experience. With every unit of it earned by the agent that
benefits from it, a self-improvement loop closes without any outcome feedback:
an agent that retains only the atoms of whatever it submitted, right or wrong,
raises its own solve rate four- to tenfold at every budget from 128 to 4096,
recovering between 3.7 and 68.1 percent of an informed ceiling as the budget
rises. We show that the same acquired experience is worth nothing
(+86, interval [-40, 222]) or a great deal (+621, interval [384, 841])
depending only on whether it can be applied before the agent's first success,
and that reserving half the search budget for an uninformed ordering converts
an acquired prior's out-of-support failure into a gain (+121, interval
[26, 213]) at no cost in support.

Finally we report four negative results that we did not soften, including a
claim withdrawn despite passing its own gate, and three predeclared gates on
transfer to a region of the space the training structures never centred on, all
of which failed. We give the diagnosis for each and state which of our design
rules we expect to survive outside this environment.

## 1. Introduction

The question we want to answer is whether a system's ability to solve
unfamiliar problems and acquire unfamiliar skills has improved, under
controlled resources and prior information. The obstacle is not the definition
but the measurement. Almost any concrete benchmark fixes a small number of task
generators, and a held-out task is then a fresh seed of a familiar generator.
Improvement measured that way is consistent with two very different things:
the system has become better at learning, or the system has become more
familiar with those particular generators.

The distinction is not academic. In the programme that preceded this work, a
verifier trained on more verified labels beat its frozen baseline by +174 on
fresh instances of six hand-written task families. Under leave-one-family-out
it was worse than the baseline on every one of the six, 716 against 1020, and
the regression grew with capacity: at 15, 60 and 120 leaves the in-distribution
totals were 1000, 1194 and 1230 while the held-out totals were 762, 716 and
706. The entire measured improvement was familiarity with six generators, and
larger models were better at acquiring it. Two further claims in the same
programme, both about improvers that select among candidate programs, were
withdrawn when a single larger pooled model on the same labels beat them by 35
and 29, and by 50 and 36.

The response to that was not a better improver but a better instrument. This
paper describes it and what it has measured so far.

**Contributions.**

1. A benchmark in which unfamiliarity is graded and drawn rather than labelled.
   Five splits (new strings, new mechanism, new latent structure, new
   combination of families, new family) are distinct questions by construction.
2. Two confirmed growth results, with predeclared thresholds, independent
   replications, structure controls, and an audit that recomputes every number
   from a decision journal and grades sampled picks through the host
   interpreter.
3. A measurement of improvement productivity rather than the value of
   experience: a lifelong setting in which the agent pays for every unit of
   experience it uses, where the loop closes with no feedback signal at all.
4. A finding we believe generalizes: when an acquired prior can be applied
   matters more than how good it is.
5. A constructive bound on the failure mode that ended every claim in the
   previous programme, namely that an acquired prior is a liability outside the
   support of what it was trained on. Hedging a fixed share of the budget
   removes the liability and costs nothing in support.
6. Four negative results reported as negatives, including one claim withdrawn
   after it passed its own gate, and a diagnosis of why a particular holdout
   could never have been crossed by anything stated over behaviour.

## 2. Positioning

We are deliberately not writing a related-work section yet. The programme this
grew out of adopted a rule that no prior work is cited until it has been read
directly, and a number of obvious neighbours, including work on self-improving
program synthesis, benchmark design for emergent ability claims, item response
models for capability measurement, observational scaling laws, proper scoring
of research forecasts, and reward-model overoptimization, have been identified
from listings and summaries rather than full texts. Citing them from summaries
would be the same error this paper is about.

The reading list is fixed and is a blocking item before submission. We state
here only the two positioning claims we are confident of, and invite
correction.

First, the benchmark's central move is to make the hypothesis space finite and
enumerable, so that a resource budget is an exact count and the oracle is the
truth rather than a maximum over observed scores. We are not aware of a
learning-ability benchmark that takes that trade, and it is the design decision
a reviewer should attack first.

Second, the distinction we draw between the *value of accumulated experience*
and *improvement productivity* is, as far as we can tell, usually left implicit.
Section 6 shows them coming apart by the whole of an effect.

## 3. The benchmark

### 3.1 Mechanisms

A mechanism is a character predicate written in the host interpreter's ordinal
expression language, so the interpreter, not the generator, decides what a
predicate means. Atoms are depth-one predicates over `ord(c)` drawn from nine
families: residues of a modulus, single bits, thresholds, popcounts and
parities of masked words, quotient residues, gcd tests, xor-then-modulus and
rotate-then-modulus. Enumerating every atom, every cross-family pair under
three boolean operators, and every complement, then keeping one representative
per distinct truth mask over a 256-character alphabet, yields a catalog of
**166,596 behaviourally distinct predicates**, of which 105,126 have density
between 0.2 and 0.8 and can therefore generate tasks.

The catalog is a function of the atom list alone. It is identified by a digest
recorded in every run that uses it.

### 3.2 Tasks

A task shows eight examples of one mechanism and hides sixteen. An example is a
string of 2 to 5 characters satisfying the predicate followed by 2 to 5 that do
not; the answer is the first block. The alphabet is `chr(0x800 + i)` for
i in [0, 256), all Unicode category Lo, so the interpreter's built-in
letter/digit transition carries no signal and the predicate has to be invented
rather than looked up.

A hypothesis is a predicate `X` read as *the answer is the longest prefix of
characters satisfying X*. It reproduces an example exactly when every character
of the first block satisfies `X` and the first character of the second block
does not, which is two integer tests against bitmasks. The rendered program is

```
Concat(Slice({"kind":"start"}, {"kind":"run","predicate":X,"ordinal":1,"side":"end"}))
```

whose interpreter reading is "up to the end of the first run of X". The two
agree in one direction only: a hypothesis passing the mask tests always passes
the interpreter, while the interpreter additionally accepts programs whose
first run begins after position zero. Grading is therefore sound and slightly
conservative. Over 31,336 audited decisions there were **zero** cases where
grading credited an answer the interpreter rejects, and 169 where the
interpreter accepts an answer grading counts as a miss, a rate of 0.54 percent;
an exhaustive scan over all arms of 400 tasks put the rate at 0.14 percent
(105 of 75,063). The true mechanism always satisfies the prefix reading, so no
task is made unsolvable by it.

### 3.3 Worlds

A **world** is a latent structure a task's mechanism is drawn from. In the main
construction a world is 14 atom keys sampled from three atom families, and its
members are the catalog rows built only from those keys and lying in the
drawable density band, typically about 150 of the 166,596. Nothing in a task
reveals the keys. A world with too few members is rejected rather than padded,
so world size never silently becomes the variable under study.

A second construction, used in section 7, defines a world behaviourally: a
centre atom plus the 14 atoms nearest it under a hidden sparse weighting over
descriptor dimensions. Every atom has a descriptor, including atoms no training
world contained, so a prior stated over that weighting is defined for them.

### 3.4 The solver interface, and why ordering is the only variable

An arm orders the catalog, scans the first `B` entries, keeps the candidates
consistent with the eight visible examples, and picks among those by one fixed
free rule (smallest positive set, ties by lowest complexity). Ordering is
therefore the only thing that differs between arms and `B` is the only
resource. Two consequences follow. "Give the baseline a larger budget" is
always available as a default, and the budget-equivalence of an arm's advantage
is directly readable.

All arms share one random tie-break. Breaking ties by catalog order, which is
complexity order, gave the free rules a systematic preference among rows they
cannot distinguish and made their solve rates jump between budgets for reasons
unrelated to their scores.

### 3.5 Splits

| split | what is fresh |
| --- | --- |
| instance | the example strings |
| mechanism | the catalog entry, never solved before, different truth mask |
| world | the key set |
| family combination | the three families in combination, each seen separately |
| family | at least one atom family no training world contained |

## 4. Protocol and statistics

Arms, splits, budgets, statistics and thresholds are fixed in a protocol
document written before the seeds are drawn. Confirmatory runs use two
replications on independent seeds and pass only if both pass. Comparisons are
paired over tasks with 20,000 bootstrap resamples; intervals are 2.5 and 97.5
percentiles of the resampled sum.

Test mechanisms are removed from every training world's solved sample, so no
tested mechanism was observed in any world.

Every confirmatory run writes a per-decision journal. An independent audit
recomputes every reported rate and every gate from the journal alone, rebuilds
the experience-free ordering and repeats the scan on sampled decisions, checks
that every recorded pick reproduces the visible examples, and runs sampled
picks through `evaluate_program`. The audit's first pass failed, which is how
the grading asymmetry in section 3.2 was found.

Runs record wall time, CPU time, peak resident memory, and the count of tasks
with no consistent candidate.

### 4.1 Screens before arms

Two preconditions are screened before any improver is built, following the
practice adopted after the previous programme.

**Power.** Eight examples leave 8.6 consistent candidates on average and a
unique one 41.9 percent of the time, and some consistent candidate is correct
on every task.

**Learnability in selection.** Given the whole consistent set at unlimited
budget, a gradient-boosted selector over 4,000 drawn mechanisms reaches 0.785
under a mechanism holdout against 0.787 for "pick the smallest consistent set"
and 0.788 for "pick the candidate most agreeing with the rest", and 0.825 under
a family holdout against 0.830 and 0.825.

| rule | mechanism holdout | family holdout |
| --- | --- | --- |
| fitted selector, 60 leaves | 0.785 | 0.825 |
| smallest consistent set | **0.787** | **0.830** |
| largest agreement with the rest | **0.788** | 0.825 |
| lowest complexity | 0.756 | 0.787 |
| random consistent candidate | 0.651 | 0.715 |

Fitting adds nothing over a free rule. **The residual is not in selection.**
Everything after this measures reaching a good hypothesis, not choosing among
the ones already in hand.

## 5. Confirmed results

Two replications, 16 worlds per split, 40 test mechanisms per world, 1,920
tasks per replication, no task without a consistent candidate. Cost: 220 s
wall, 254 s CPU, 192 MB peak for both replications. The audit passes: every
rate and every gate recomputed to the reported value, all 3,840 rebuilt picks
matched, no pick inconsistent with its visible examples, no tested mechanism in
the experience pool used to choose for it.

### 5.1 G1: experience of a structure, on unfamiliar mechanisms of that structure

At a budget of 256 of 166,596, over the 1,920 tasks of a replication:

| comparison | replication 1 | replication 2 |
| --- | --- | --- |
| experience of 32 of the world's mechanisms minus the best experience-free ordering | **+1601** | **+1603** |
| minus the same rule fed another world's mechanisms | **+1643** | **+1644** |

Solve rates at that budget: 0.034 to 0.048 for catalog order, 0.003 to 0.009
for density order, 0.005 to 0.052 for another world's experience, 0.852 to
0.902 for the world's own. The development curve is monotone in experience:
0.001, 0.018, 0.057, 0.165, 0.326, 0.644, 0.775, 0.803 at 0, 1, 2, 4, 8, 16, 32
and 64 solved mechanisms.

At 64 solved mechanisms and a budget of 256, experience beats every free
ordering *at unlimited budget*, because the ordering also places good
hypotheses ahead of bad ones among those it reaches.

We report G1 as the floor and note that it is close to tautological: knowing
which 150 of 166,596 hypotheses matter is worth a great deal. Its value is that
the wrong-world control makes it a clean instrument check, and that no arm here
fits a model. The ordering is a count of atom occurrences, so no gain can be
credited to capacity.

### 5.2 G2: experience of other structures, on a structure never seen

Worlds whose three atom families were each trained on but never in this
combination. Budget 1024, tasks out of 640, both replications:

| k | minus the best free rule | minus the no-structure control | minus the label-scrambled control |
| --- | --- | --- | --- |
| 1 | +127 [103, 150] / +127 [102, 152] | +110 [86, 134] / +127 [102, 152] | +119 [95, 142] / +128 [103, 153] |
| 2 | +190 [163, 217] / +188 [163, 214] | +176 [152, 200] / +185 [161, 210] | +191 [167, 215] / +166 [141, 191] |
| 4 | +204 [178, 230] / +201 [174, 227] | +219 [193, 245] / +189 [162, 216] | +214 [189, 239] / +170 [144, 196] |

Every interval entirely positive, and the same sign at every budget from 256 to
16,384. The no-structure control is the identical estimator fitted on worlds
drawn without family structure; the scrambled control is the same fitted
estimator with its atom labels permuted.

**Sample efficiency.** At budget 1024, one solved mechanism plus experience of
400 other worlds reaches 0.331 and 0.338, which the free rule needs four to
five solved mechanisms of the new world to match.

The mechanism is legible. A world takes 14 keys from three families, so atoms
of one family co-occur across training worlds; the prior generalizes from an
observed atom to atoms that travelled with it. That is why it reaches an
unfamiliar combination of families, and why section 7 goes the way it does.

## 6. Compounding, and the earned loop

The results in this section have controls and intervals but no predeclared
gate. We label them development evidence.

### 6.1 Compounding

G2 is a level: a fixed quantity of prior experience buying a fixed advantage.
Compounding is a claim about the derivative. Fitting the same estimator on the
first 25, 50, 100, 200 and 400 training worlds, and reading the margin over the
free rule on 20 worlds whose family combination no training world used,
800 tasks:

| k | budget | 25 | 50 | 100 | 200 | 400 | 400, unstructured |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1024 | -26 | -7 | +20 | +37 | +54 [29, 80] | -4 [-26, 18] |
| 2 | 1024 | +21 | +60 | +79 | +90 | +122 [94, 150] | -14 [-37, 8] |
| 4 | 1024 | +20 | +47 | +55 | +94 | +104 [77, 131] | -20 [-41, 1] |
| 1 | 4096 | -95 | -96 | -67 | -35 | +5 [-19, 29] | -64 [-82, -47] |
| 2 | 4096 | -146 | -101 | -47 | -10 | +43 [19, 67] | +10 [-8, 28] |
| 4 | 4096 | -77 | -20 | +33 | +80 | +102 [73, 131] | -35 [-64, -7] |

Monotone in all six cells, not flattened at 400 worlds. The control sweep on
worlds drawn without family structure is flat or negative everywhere and never
becomes monotone, so this is structure accumulating rather than an estimator
warming up.

Two cautions. This is not recursive: the estimator that turns worlds into a
prior is fixed and only its input grows. And the small-sample cells are a
warning, not noise: a prior fitted on 25 worlds is worse than no prior, by -95
to -146 with intervals entirely negative.

### 6.2 The earned loop

Everything above hands an arm its solved mechanisms. Solving them cost budget
and none of it was charged, so sections 5 and 6.1 measure the value of
accumulated experience and not improvement productivity.

An agent meets 120 tasks from one world, each a mechanism it has never seen,
spends the same scan budget on every one, and starts knowing nothing. Whatever
it learns comes from tasks it has already paid for, so total resource is
identical across arms. The task stream is shared, so every comparison is paired
on the same mechanisms in the same order. 24 worlds.

| arm | B=256 | first 10 to last 10 | B=1024 | first 10 to last 10 |
| --- | --- | --- | --- | --- |
| never updates | 0.8 | 0.008 to 0.013 | 1.8 | 0.021 to 0.013 |
| keeps the atoms of whatever it submitted | 3.5 | 0.013 to 0.037 | **19.7** | 0.037 to **0.292** |
| keeps them only when told it was right | 2.4 | 0.013 to 0.017 | 17.2 | 0.042 to 0.287 |
| told the true mechanism every time | 95.6 | 0.250 to 0.883 | 99.0 | 0.300 to 0.925 |

Against the arm that never updates: +429 [289, 576] and +371 [255, 493] at
budget 1024; +66 [28, 112] and +40 [12, 72] at 256.

**The loop closes, and it closes without feedback.** The blind arm consults
nothing outside the task. Every candidate it submits was consistent with eight
examples, which is apparently enough for its atoms to be worth keeping even
when the answer was wrong, and it is at least as good as the arm told whether
it was right. One bit of outcome feedback per task buys nothing here.

**There is no takeoff threshold.** Six budgets, 16 worlds of 100 tasks:

| budget | never updates | blind | informed ceiling | blind, first 20 to last 20 | blind minus static |
| --- | --- | --- | --- | --- | --- |
| 128 | 0.2 | 1.8 | 48.5 | 0.003 to 0.031 | +25 [4, 51] |
| 256 | 0.5 | 4.9 | 78.5 | 0.013 to 0.091 | +71 [19, 144] |
| 512 | 0.7 | 8.7 | 82.2 | 0.022 to 0.172 | +128 [69, 199] |
| 1024 | 1.3 | 13.3 | 80.6 | 0.044 to 0.219 | +192 [118, 280] |
| 2048 | 1.8 | 28.2 | 79.4 | 0.084 to 0.447 | +422 [299, 544] |
| 4096 | 3.4 | 53.2 | 78.1 | 0.200 to 0.772 | +796 [730, 858] |

The loop closes at every budget with an interval entirely positive, and the
last-twenty rate is 4 to 10 times the first-twenty rate throughout. What grows
with the budget is the share of the informed ceiling recovered: 3.7, 6.2, 10.6,
16.5, 35.5 and 68.1 percent. The ceiling saturates by budget 256, because an
agent told the true mechanism knows its world's 14 atoms within a few tasks.
The earned agent is limited by the rate at which correct atoms arrive, and the
budget only sets that rate. An earlier two-point version of this measurement
suggested a threshold; six points show a smooth curve and none.

### 6.3 When a prior applies matters more than how good it is

The prior confirmed in G2 does not accelerate the earned loop: +86 [-40, 222]
at budget 1024 and +34 [-1, 83] at 256, both crossing zero. The reason is
structural rather than statistical. That prior conditions on the atoms of
mechanisms the agent has already solved, and an agent that has solved nothing
has nothing to condition on, so for exactly the stretch that decides whether
the loop starts it is the no-experience ordering.

What the training worlds also know, and that prior never used, is which pairs
of atoms belong together in any world at all. That is unconditional and
available before the agent sees a single task. Starting the earned agent from
that ordering and changing nothing else, tasks solved of 100, 16 worlds:

| group | budget | static | earned loop | cold-start prior | permuted control | ceiling |
| --- | --- | --- | --- | --- | --- | --- |
| families training held | 256 | 0.6 | 3.4 | **23.0** | 3.9 | 84.6 |
| families training held | 1024 | 1.9 | 13.6 | **52.4** | 17.6 | 83.4 |
| a family it did not | 256 | 0.3 | 2.3 | 7.2 | 5.4 | 81.2 |
| a family it did not | 1024 | 1.3 | 13.7 | 10.7 | **19.9** | 81.4 |

On familiar families: **+314 [193, 432]** and **+621 [384, 841]** over the
earned-loop champion, with the permuted control beaten by +306 [212, 396] and
+558 [350, 763]. The share of the informed ceiling recovered goes from 4 to 27
percent at budget 256 and from 16 to 63 percent at 1024. Most of that is
knowing which atoms appear in worlds at all rather than which pairs go
together: replacing pair co-occurrence with each atom's own rate loses only
+56 [17, 102] at 256 and +53 [-5, 106] at 1024.

Outside the trained family support the same prior is worse than its permuted
control, -147 [-240, -60] at budget 1024.

### 6.4 Hedging bounds the loss

Every acquired prior in this work fails in one place and no other. Two repairs
are available. **Hedge**: reserve a fixed share of the scan budget for the
ordering the agent would use with no prior, which needs nothing to be
detectable because the loss is bounded by the reserved share whatever the prior
believes. **Detect**: switch the prior off when the fraction of the agent's own
solved atoms appearing in no training world exceeds the share a hedge would
have reserved.

| group | budget | prior | hedge 25% | hedge 50% | detector |
| --- | --- | --- | --- | --- | --- |
| familiar families | 256 | +274 [176, 412] | +263 [170, 389] | +235 [164, 327] | +274 [176, 412] |
| familiar families | 1024 | +298 [134, 507] | +301 [158, 496] | **+325 [186, 515]** | +298 [134, 507] |
| unfamiliar family | 256 | +95 [46, 146] | +98 [50, 147] | +87 [46, 130] | +95 [46, 146] |
| unfamiliar family | 1024 | **-5 [-93, 76]** | +65 [-32, 165] | **+121 [26, 213]** | -5 [-93, 76] |

Reserving half the budget converts the out-of-support failure into a gain and
costs nothing in support. The detector never fired in any group at any budget:
foreign atoms imported from wrong answers come mostly from the families
training did contain, so the statistic is diluted. The hedge needs no
statistic.

## 7. Negative results and the support boundary

### 7.1 A claim withdrawn despite passing its gate

G3 asked whether an acquired prior transfers to a world containing a family no
training world held. Its gate read budget 1024, at k of 2 and 4, and it passed:
+35 [12, 58] and +22 [2, 42] in one replication, +33 [13, 53] and +23 [4, 42] in
the other, with the permuted control beaten in all four cells.

The same comparison at other budgets, same runs:

| budget | k=1 | k=2 | k=4 | k=8 |
| --- | --- | --- | --- | --- |
| 256 | +13 / +13 | +29 / +12 | **-16 / -17** | **-18 / -52** |
| 1024 | +7 / -5 | +35 / +33 | +22 / +23 | +22 / +7 |
| 4096 | **-46 / -63** | **-41 / -39** | -10 / +3 | +21 / +42 |
| 16384 | +46 / +57 | +29 / -1 | -17 / -8 | -26 / -9 |

Bold cells have intervals entirely negative. A gain confined to one budget with
significant losses on either side is a budget-specific artifact. Reading the
gate at a single budget was selection even though it was declared in advance.
We withdrew G3 and made "read a gate across the whole resource range" a
standing rule.

### 7.2 Why that boundary could never have been crossed

Four attempts to transfer to a world built from a family no training world
contained failed. A fifth measurement explains all four.

Clustering the 368 atoms by the whitened Fourier and Walsh magnitude spectra of
their truth masks and asking how well the clusters recover the nine families
gives, at the best k over 6 to 32, **adjusted Rand 0.144**. Per family:
`threshold` is recovered perfectly, `parity` 0.86, `bit` and `rotmod` 0.75, and
the two normally withheld families are captured at 0.69 and 0.47 with 0.68 and
0.72 of their home clusters foreign.

This is not a weak descriptor so much as a category that is not behavioural. In
these worlds a family is the *name of an arithmetic operation*: `mod:2:0` and
`mod:16:7` share a label and nothing observable. The family holdout asked for
generalization across a boundary nothing computable on an atom can see, and no
representation defined on behaviour could have crossed it. The repeated failure
is a fact about how the worlds were built, not a law about transfer, and it
retro-explains the verifier collapse described in section 1.

### 7.3 Three predeclared gates on a boundary that is crossable in principle

We rebuilt worlds behaviourally: a hidden sparse weighting over descriptor
dimensions, drawn once per replication and shown to nobody, with a world a
centre atom plus the 14 atoms nearest it under that weighting. Every atom has a
descriptor, so a prior stated over the weighting is defined for atoms no
training world contained.

| gate | what it asked | outcome |
| --- | --- | --- |
| G4 | a fitted metric beats the free unweighted rule *and* a dimension-permuted copy of itself, at every budget | **failed** on the control clause: beat the free rule in 15 of 16 cells, indistinguishable from the permuted copy at budgets 256 and 16,384 |
| G5 | the same with the target made identifiable | **failed** one cell of sixteen in each replication, k=2 at budget 256 |
| G6 | the same with doubled power at fixed effect size | **failed**: replication 1 passed every cell, replication 2 failed three |

Between G4 and G5, two screens found that G4 had asked for something not
identifiable. Fitting to squared differences rather than elementwise products,
which is the form a weighted distance actually takes, moved recovery of the
true active dimensions from 0.28 to 0.29, so the estimator was not fitted to
the wrong thing. The catalog has 368 atoms and the descriptor 385 dimensions,
so a weighting over those dimensions is not determined by the distances among
those points:

| descriptor width | 8 | 16 | 32 | 64 | 128 | 385 |
| --- | --- | --- | --- | --- | --- | --- |
| active dimensions recalled | 1.00 | 1.00 | **0.92** | 0.90 | 0.70 | **0.33** |
| correlation with the truth | 0.84 | 0.92 | 0.90 | 0.86 | 0.85 | **0.13** |

G5 repeated the question at width 32 with 8 active dimensions, both fixed in
the protocol before any task was run at that width. The weighting was recovered
at Pearson 0.939 and 0.976 and the metric beat both comparisons in 15 of 16
cells in each replication. The one cell it failed, k=2 at budget 256, is where
the protocol asked for something close to unattainable: in one replication the
*true* weighting beats the free rule there by only +19 [3, 35], so a floor of
+15 demanded four fifths of all the headroom in the cell. A floor stated as an
absolute count and applied uniformly to cells with very different headroom is a
protocol flaw of the same species as G3's, and we record it as one.

G6 added power at a fixed effect size and nothing else: 32 worlds per split,
1,280 tasks, floor scaled from +15 of 640 to +30 of 1,280, fresh seeds.
Replication 1 passed every cell. Replication 2 failed three, and not only for
want of power: at k=2 and budget 256 the permuted copy beat the metric itself,
-22 [-36, -9].

**No claim is made.** Every cell at budgets 4096 and 16,384, in every
replication of G5 and G6, is positive against both comparisons with intervals
entirely positive, some by +196 to +224. That is a description, not a claim. A
fourth gate restricted to those budgets would be a range chosen from results
already seen, which is what withdrew G3, so we stopped. What the environment
has established is that the headroom is real, that an identifiable target is
recovered almost exactly, and that converting recovery into a reliable margin
at every resource level is not something a diagonal metric over these
descriptors does.

### 7.4 Two estimator upgrades that looked right and were not

Replacing pairwise-maximum affinity with joint retrieval over training worlds,
which is the better-specified model of the generative process, loses by -22 to
-54 of 640 across the seen-combination and new-combination splits, with
intervals entirely negative in most cells. Weighting concentrates the estimate
on the handful of training worlds containing the one to four observed atoms,
while a maximum over pairwise counts pools the same evidence across every world
containing that atom. At the evidence levels where a prior is worth having, the
cruder summary is the more robust one.

The out-of-support detector of section 6.4 never fired.

## 8. Discussion

We separate the rules we expect to survive outside this environment from the
ones that may be artifacts of it.

**Likely to generalize.**

1. *An acquired prior must never overrule present evidence.* The one collapse
   we observed was entirely this: an atom observed solving a task in the world
   at hand was assigned zero probability because training had not seen it.
   Score every hypothesis at least as high as present evidence alone would.
2. *Hedge every acquired prior.* Reserving a share of the budget for the
   uninformed rule bounds the loss where the prior does not apply, needs no
   detector, and cost nothing in support in our measurements.
3. *Generalization reaches exactly as far as the representation it is stated
   over.* An identity prior cannot reach an unseen atom by construction. The
   evaluator-side corollary is that a holdout must cross a boundary the
   representation can see, or its failure is a property of the labelling.
4. *When a prior applies matters as much as how good it is.* The same
   experience was worth +86 [-40, 222] or +621 [384, 841] on when it could be
   applied.
5. *Charge the experience, or you are measuring a different quantity.* The
   value of accumulated experience and improvement productivity came apart by
   the whole of the effect.

**Methodological, and we would apply them anywhere.**

6. The adversarial default must include model capacity.
7. Read a gate across the whole resource range, and check its threshold is
   attainable before running it.
8. The free rule in an arm's class must be the best free rule available.
9. Tie-breaks are part of an arm.
10. Do not read a threshold off two points.

**Possibly artifacts of this environment.** That a cruder estimator beats a
better-specified one; that outcome feedback is worth nothing in the earned
loop; the precise shape of the ceiling-recovery curve.

## 9. Limitations

- One environment, one task form, one alphabet, one hypothesis language. Every
  rule above is a conjecture outside it.
- The hypothesis space is finite and enumerable by construction. This is what
  makes budget countable and the oracle exact, and it is the assumption most
  worth attacking.
- Grading reads a predicate as the longest satisfying prefix while the
  interpreter also accepts a later first run. Sound and 0.14 to 0.54 percent
  conservative, uniformly across arms.
- No forecast was committed before any run. The programme this belongs to asks
  for proper-scored predictions and we have none.
- G1 is close to tautological and we say so.
- Two early screens ran on an earlier catalog build and do not import against
  the current module. They are marked superseded in the source; the
  load-bearing one was re-established on the current build.
- The cold-start comparison reserved evaluation mechanisms from training by
  index order rather than by the shuffled stream. The prior is a function of
  atom keys alone, so no answer can leak, but that run should be repeated
  before the number is quoted outside this draft.
- Nothing here is recursive. Compounding grows the estimator's input; nothing
  improves the estimator, and the earned agent runs one fixed rule for its
  whole life.
- Related work is unread. See section 2.

## 10. Conclusion and future work

An instrument in which unfamiliarity is drawn rather than labelled makes four
questions separable that are routinely merged, and makes a negative result cost
a minute rather than a day. On it, experience of a latent structure improves
the solving of unfamiliar mechanisms from that structure, and experience of
many structures improves the acquisition of one never seen. Both survive
predeclared thresholds, two replications, structure controls and an independent
audit. With experience charged to the agent that uses it, a self-improvement
loop closes and needs no feedback, and the single largest lever we found is a
prior that can be applied before the agent's first success.

Four things are open, in the order they block.

1. Make an acquired prior reliably useful at every resource level, or show it
   cannot be. Three gates failed with the same shape. Two hypotheses are
   testable in under an hour on this instrument: either the head of the
   ordering is decided by concentration rather than direction, measurable by
   comparing orderings rather than outcomes, or the fitted weights are accurate
   in aggregate and wrong about the few atoms that matter most at the head. The
   next study must fix its budget range by a rule stated and justified before
   it runs.
2. Make the earned loop's ceiling reachable. The gap between 0.292 earned and
   0.925 informed is entirely the rate at which correct atoms arrive. Active
   choice of which hypothesis to submit, when a likely-wrong one would be more
   informative, is untouched.
3. A second task form in the same catalog, to separate growth in this
   environment from growth in this readout. This is the cheapest item and the
   one that most affects how far any of this generalizes.
4. Recursion. The instrument can ask whether the procedure that turns
   experience into a prior can itself be improved from that experience. We have
   not asked it.

## Appendix A: reproducibility

Everything runs on one workstation in Python 3.12 with numpy and
scikit-learn. The environment and harness are two modules; each experiment is
one script writing one JSON analysis file that refuses to overwrite itself.
Thirteen tests cover the load-bearing invariant, which is that the bitmask
grading agrees with the host interpreter candidate by candidate.

| step | cost |
| --- | --- |
| catalog build, 166,596 rows | 0.2 s, 65 MB |
| a development screen | 15 to 90 s |
| confirmed run, two replications | 220 s wall, 254 s CPU, 192 MB |
| independent audit, 31,336 interpreter checks | 238 s |
| the whole sequence in this paper | under one hour of compute |

Artifact inventory. Environment and harness: `rsi/mechanism_space.py`,
`rsi/mechanism_worlds.py`, `tests/test_mechanism_space.py`. Screens and
development runs: `mechanism_selection_recheck.py`,
`mechanism_world_growth.py`, `mechanism_meta_growth.py`,
`mechanism_meta_support.py`, `mechanism_meta_transfer.py`,
`mechanism_family_transfer.py`, `mechanism_metric_transfer.py`,
`mechanism_compounding.py`, `mechanism_lifelong.py`, `mechanism_takeoff.py`,
`mechanism_cold_start.py`, `mechanism_hedged_start.py`,
`mechanism_world_retrieval.py`, `mechanism_atom_clustering.py`,
`mechanism_metric_worlds.py`, `mechanism_metric_form.py`,
`mechanism_metric_identifiability.py`. Confirmations:
`EXPERIMENT-mechanism-growth-confirmation.md` with
`mechanism_growth_confirmation.py` and
`audit_mechanism_growth_confirmation.py`;
`EXPERIMENT-metric-world-transfer-confirmation{,-2,-3}.md` with
`metric_world_confirmation{,2,3}.py`. Results record:
`MECHANISM-GROWTH-RESULTS-2026-09-21.md`. Prior programme:
`WHAT-WORKED-WHAT-FAILED-2026-09-21.md`.
