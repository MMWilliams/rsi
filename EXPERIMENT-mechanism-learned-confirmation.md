# Predeclaration: a representation learned from worlds, and its growth

Written 2026-09-23, before the confirmatory seeds are drawn. Every threshold,
arm, split and statistic below is fixed here; the run reports them whether they
pass or fail. Development evidence: `analysis/mechanism-learned-groups-*.json`
and `COACH-RESULTS-2026-09-23.md`.

## 1. Background

C-family (`EXPERIMENT-mechanism-family-confirmation.md`, passed and audited)
showed that an earned-loop agent keeping a posterior over which three families
its world uses acquires unfamiliar worlds faster at every budget, including the
tight ones nothing else moved. Its families were read from the program text.
Here the agent reads nothing: it learns which atoms belong together from which
atoms appear together across training worlds.

## 2. The agent and the claims

The **learned-group agent** is the C-family agent with its families replaced by
groups from `rsi.learned_groups.learn_groups(select='likelihood')`: atoms
clustered by spectral clustering of positive pointwise mutual information of
co-occurrence across training worlds, the number of groups (3 to 12) chosen as
the one under which the last fifth of the training worlds is most probable when
clustered on the first four fifths, under "a world picks three groups and
draws its atoms from their union, each atom slipping with probability 0.05".
Atoms no training world contained form one extra group. Uniform prior over
triples of groups, slip 0.2, weight 2, no hedge at 128 and 256, half from 512.
The champion's pair prior is fitted on the first 400 training worlds for every
arm; groups are learned from the first 400 (`early`) and from all 1,600
(`learned`).

**C-learned.** The learned-group agent with groups from 1,600 worlds solves more
tasks than the champion at every budget from 128 to 4096 on worlds of trained
and of untrained family combinations, and is not significantly worse at any
budget on worlds of a family no training world held. Gated exactly as C-family.

**C-growth.** Its acquisition improves with the experience the representation
is learned from: the agent on groups from 1,600 worlds solves more than the
same agent on groups from 400, summed over every split and budget.

## 3. How the configuration was chosen

On seed 632101 eigengap-selected groups recovered the families at adjusted
Rand 0.15, 0.84, 0.89, 0.89 from 100, 400, 1600 and 6400 worlds, merging small
families. On seed 633101 the agent on them recovered about 80% of the
syntactic agent's in-support gains and lost at 256 on untrained-family worlds.
Selection by held-out likelihood (5-6 groups) replaced the eigengap; on seed
634101 the agent then matched the syntactic agent everywhere; on the untouched
seed 635101 at 64 worlds per split it matched it again (for example +313 vs
+310 at 128 and +755 vs +677 at 2048 on untrained combinations), with the same
two weak cells as the syntactic agent: untrained combinations at 512 (+53
[-69, 180]) and untrained-family worlds at 256 (-69 [-153, 10]). Groups from
1,600 worlds beat groups from 400 in 15 of 18 cells there. Weight, slip and
hedge are C-family's, unchanged.

## 4. Evaluation and gates

`mechanism_learned_confirmation.py`, whose constants this quotes. Per
replication: 1,600 training worlds from 80% of the combinations of seven
families, 128 held-out worlds each of `seen_triple`, `new_triple` and
`new_family`, streams of 100 tasks, their mechanisms removed from every
training world's solved set. Champion, learned (1,600) and early (400) agents
each live every world once at each of six budgets. Paired over worlds, 20,000
bootstrap resamples, 2.5 and 97.5 percentiles.

A replication passes **C-learned** if on `seen_triple` and `new_triple` every
one of the six budgets has the learned-minus-champion interval entirely above
zero (12 cells) and on `new_family` none of the six has it entirely below zero
(6 cells). It passes **C-growth** if the sum over all 18 split-budget cells of
learned minus early, resampling worlds within each split, has its interval
entirely above zero. Each claim passes only if both replications pass it.

**Power.** Pooled over the two development seeds the weakest C-learned cell is
`new_triple` at 512, about 1 task per world, expected z near 1 at 128 worlds:
this cell may well fail, as it might have for C-family, which passed it
(+248, +722). The gate is not relaxed for it.

## 5. Audit

`audit_mechanism_learned_confirmation.py`: catalog digest and journal hashes;
both groupings relearned from the recorded training worlds and required equal
to the recorded labels; every total, contrast, growth figure and gate
recomputed from the journal; every pick checked against constraints rebuilt
from the example strings; 3,000 sampled picks through the host interpreter; no
tested mechanism among training solved sets; sampled lifetimes of all three
arms replayed decision for decision by `rsi/learned_reference.py`
(`tests/test_learned_groups.py` holds the fast agent to it).

## 6. What a pass would and would not mean

C-learned passing would make C-family's gain the product of a representation
the agent learned from experience of worlds rather than one written into it.
C-growth passing would show that representation, and the acquisition it
supports, improving with experience past the point where the pair prior
stopped. Together they would be the programme's first predeclared, audited
instance of an ability to acquire unfamiliar skills that grows with experience
of other worlds at every resource level. One environment, one task form, one
hypothesis language; the within-world learner is still a fixed rule.

A failure of either is reported as one; no second run will be predeclared on
the strength of its arms.

Replication seeds: A 981101, B 982101.

Frozen: 2026-09-23. SHA-256: runner `mechanism_learned_confirmation.py`
1ce2632ef1ccf3ffb8367b6d917720eca8d5bb622610755ce38044800a5dad79; groups
`rsi/learned_groups.py` 4a03adf268b5a28f5928a1783ae3ab45b32328fb6d2f03da7271eeb7df149af7;
family model `rsi/family_inference.py` 65535041dd581ae16a2bf4d43f16be2048829a369359009f8f6d276122520dc4;
simulator `rsi/growth_coach.py` bb22f9a0193258b8e3bc9c94f766ee639d76ce5aaa683f9aba996f5ed61af868;
reference `rsi/learned_reference.py` 7a884dd7a86705cac45d68dd627b8419c209f7ff462f04f98daa1daefca888ee;
audit `audit_mechanism_learned_confirmation.py` 2982da7ba9821085d562e9621d104c5daf8df545b4a8d6bc2c7e6034e623e289.
