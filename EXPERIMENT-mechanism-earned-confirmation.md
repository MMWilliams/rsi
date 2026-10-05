# Predeclaration: a representation learned from the agent's own experience

Written 2026-10-05, before the confirmatory seeds are drawn. Every threshold,
arm, split and statistic below is fixed here; the run reports them whether they
pass or fail. Phase 1 of `PROGRAMME-RECURSIVE-2026-10-04.md`.

## 1. Background

C-growth (`EXPERIMENT-mechanism-learned-confirmation.md`, passed, audited)
learned atom groups from each training world's true atom set, handed over.
Rule 11 (charge the experience) was applied at levels 0 and 1 but not at the
level where the representation is built. Here nothing about a training world
reaches the representation learner except through the agent's own picks.

## 2. The agent and the claim

Each training world is lived by the **blind earned loop** (no cross-world
knowledge, keeps the atoms of whatever it submitted, never told whether it was
right) for 100 tasks at budget 4096. Its **earned set** is the atoms appearing in
at least 3 of its submitted picks in that world. Across worlds, atoms present in
fewer than 50 earned sets are left ungrouped (they join the unseen group the
agent treats neutrally); the rest are clustered by
`rsi.learned_groups.learn_groups(select='likelihood')`, as in C-growth. If too
few atoms clear the bar to cluster, the agent has no grouping and plays the
champion. The family agent on the grouping is C-family's (uniform prior over
group triples, slip 0.2, weight 2), with the hedge at half the budget from 256
and none at 128.

Arms, each living every held-out world once at six budgets: the champion;
groups from 1,600 earned worlds (`earned`), from the first 800 (`mid`) and the
first 400 (`early`); `earned`'s labels permuted across atoms (`permuted`); and
groups from 1,600 handed true sets, the C-growth arm (`handed`, upper
reference). The champion's pair prior is fitted on 400 handed worlds in every
arm, as in C-growth, so the grouping is the only difference. Earning is charged:
655,360,000 scans per replication, reported.

**C-earned** passes in a replication if all three hold:
1. **growth**: `earned` minus `early`, summed over all 18 split-budget cells,
   has its interval entirely above zero;
2. **structure**: `earned` minus `permuted`, summed the same way, has its
   interval entirely above zero;
3. **safety**: in none of the 18 cells is `earned` minus champion entirely below
   zero.

It passes only if both replications pass.

Reported, not gated: per-cell `earned` minus champion (and whether each is above
zero), `mid` minus `early` and `earned` minus `mid` (rule 13: growth is not read
off two points), `handed` minus `earned`, and `earned`'s share of the handed
reference's pooled gain.

## 3. How the configuration was chosen

Seed 641101 (32 worlds per split): groups from blind earning at the deployment
budget lose to the champion at 128-256; earned at 4096 they looked close to
handed. Seed 643101, the first rehearsal of this runner (128 worlds per split),
refuted that: earned-at-4096 lost at 256-512 and 1,600 earned worlds were worse
than 400 (-1103). Earned sets were 63% precise; keeping atoms in at least 2 or 3
picks raised precision to 0.86 and 0.94 and did not help. The cause was
discovery bias: blind earning recovers mod atoms at 0.74-0.84 and rotmod and gcd
at 0.21-0.31, so earned groupings recover the families at adjusted Rand
0.17-0.55 (handed 0.87). Earning each generation with the previous generation's
groups raised solves per world from 27 to 36 but not the grouping (ARI 0.40,
0.53, 0.36, 0.40). Leaving atoms with fewer than c earned worlds ungrouped did:
at m=3, c in {0, 10, 25, 50} gave ARI 0.52, 0.61, 0.63, 0.89 and pooled gains
over the champion of +367, +589, +600, +1436 (handed +2733). Eight
configurations were compared on that opened seed; m=3, c=50 was taken.

On the fresh seed 644101 that configuration gave growth +5216 [4129, 6321] and
structure +7458; no atom cleared the bar at 400 worlds, so `early` played the
champion. One cell was significantly below the champion (new_family at 256,
-211), the unhedged cell. With the hedge from 256 it was -39 [-110, 30], no cell
was significantly negative, and growth was +4797 [3805, 5794]; that hedge is
taken. Every-cell improvement over the champion is not gated because the handed
true-set reference fails it at 256 and 512 on untrained combinations on that
seed (-27, -6), so it would test the family agent, not earning. The `mid` arm
was added after that and run once on 644101 with the final runner and audit
(audit passed): growth +4797, structure +6675, safety held in all 18 cells,
`earned` recovered 47% of the handed reference's gain; `mid` minus `early` was
+146 [-610, 894] and `mid` lost to the champion at 256-1024 on trained
combinations, so on that seed growth was a threshold between 800 and 1,600
worlds, not a slope. Expected here as well; reported, not gated.

## 4. Evaluation

`mechanism_earned_confirmation.py`, whose constants this quotes. Per
replication: 1,600 training worlds from 80% of the combinations of seven
families, 128 held-out worlds each of `seen_triple`, `new_triple` and
`new_family`, streams of 100 tasks whose mechanisms are excluded from every
training world's earning stream and solved set. Paired over worlds, 20,000
bootstrap resamples, 2.5 and 97.5 percentiles; pooled statistics resample
worlds within each split and add the splits' sums.

**Power.** On 644101 the growth and structure margins are about five standard
errors; the safety gate's weakest cells (untrained combinations at 256-512,
untrained-family at 256) have upper bounds of +13 to +30, so safety is the gate
most likely to fail.

## 5. Audit

`audit_mechanism_earned_confirmation.py`: catalog digest and journal hash;
every earned set rebuilt from the journaled picks through the reference key
table; all five groupings relearned or re-permuted and equal to the recorded
labels; six earning lifetimes regenerated from their recorded streams, every
pick checked against constraints rebuilt from the example strings and replayed
decision for decision by `rsi/learned_reference.py` with the blind coach; every
total, contrast and gate recomputed from the journal; every evaluation pick
checked against rebuilt constraints; 3,000 sampled picks through the host
interpreter; no tested mechanism in any training world's solved set or earning
stream; sampled lifetimes of all arms replayed by the reference.

## 6. What a pass would and would not mean

A pass would make the C-growth representation the agent's own: learned only
from what the agent itself found, charged in scans, improving with the worlds
it has lived, on held-out worlds at every budget without loss. Levels 0, 1 and 2
would then all be earned. It would not make the representation learner itself
improve (it is still researcher-written, with an evidence bar chosen on
development seeds), and it says nothing about another environment family, task
form or hypothesis language. One environment.

A failure is reported as one; no second run will be predeclared on the
strength of its arms.

Replication seeds: A 991101, B 992101.

Frozen: 2026-10-05. SHA-256: runner `mechanism_earned_confirmation.py`
e651040012eec5dfa298f8b66380b9c3c5265a5550dcccc1edf2919b7db6bc79; audit
`audit_mechanism_earned_confirmation.py`
b2bf5cdd7267e64169b4654b1113b7d99becf3e793bfe8ded26ae2a55c7d6d53; groups
`rsi/learned_groups.py` 4a03adf268b5a28f5928a1783ae3ab45b32328fb6d2f03da7271eeb7df149af7;
family model `rsi/family_inference.py` 65535041dd581ae16a2bf4d43f16be2048829a369359009f8f6d276122520dc4;
simulator `rsi/growth_coach.py` bb22f9a0193258b8e3bc9c94f766ee639d76ce5aaa683f9aba996f5ed61af868;
reference `rsi/learned_reference.py` 7a884dd7a86705cac45d68dd627b8419c209f7ff462f04f98daa1daefca888ee.
