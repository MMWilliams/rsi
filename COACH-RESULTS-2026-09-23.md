# A coach trained by reinforcement learning, for the earned loop

Started 2026-09-22 on the question: can an external component, trained by
reinforcement learning and continually fine-tuned, nudge the earned loop of
`MECHANISM-GROWTH-RESULTS-2026-09-21.md` §6 into growing faster? Every number
below is read from a named analysis file. §2-10 and §13 are development
evidence; §11, §12 and §14 are predeclared confirmations with independent
audits.

**Short answer.**

0. **Confirmed (§14): a family-level world model moves the tight-budget wall.**
   An earned-loop agent that keeps a posterior over which three families its
   world uses, from its own evidence, solves more tasks than the champion at
   every budget from 128 to 4096 on trained and untrained family combinations
   and loses nowhere on worlds of an untrained family, in both replications
   (+248 to +1,635 of 12,800; about double at budget 128 on untrained
   combinations). It is a written representation, not a trained component.
1. Where the loop receives evidence (budgets of 1024 scans and up) a coach
   trained by evolution strategies on the lifetimes of other worlds lifts the
   earned loop a great deal on worlds it never lived in, including worlds of a
   family no training world contained: in the confirmation's two replications,
   +664 to +2,165 of 12,800 tasks per split at 1024-4096, every interval far
   above zero, and no significant loss at any tighter budget (§11).
2. **The RL coach's predeclared claim failed twice and the line is closed.**
   The first time its high-confidence deployment step was underpowered (§11);
   with validation sized up, it deployed at 256 and the coach lost there on
   untrained combinations (§12). The coach's clean ungated record in the first
   confirmation is not claimed.
3. Where the loop receives almost no evidence (128-512) there is almost nothing
   for any *policy* to do: in-sample optima recover at most 8% of the gap to
   the informed ceiling, about 1% at 256 (§2-3); near-misses carry no signal,
   rotation does not help, and the pair prior stops improving at about 400
   training worlds (§4). What moves it is a better *representation* (§13-14).
4. The audit's replay check found a simulator bug that had manufactured the
   most dramatic development failures; they are withdrawn (§9).
5. The hedge rule was read at one budget and is wrong at another (§5).

## 1. The component

`rsi/growth_coach.py`. The earned loop orders the catalog, scans `B` rows per
task, submits by the free rule and keeps the atoms of what it submitted. The
coach is a parameter vector that sets every free choice in that loop and
nothing else, so it can only act through the loop's own evidence:

| field | what it sets |
| --- | --- |
| unknown | how far rows built from atoms without evidence are pushed down |
| pair | weight on the cross-world pair co-occurrence prior |
| count | weight on repeated evidence, log(1 + count) |
| depth1 | bonus for depth-one rows |
| affinity | weight on P(atom \| a known atom) from the training worlds |
| soft | evidence credited to other consistent candidates in the window |
| pick | preference, among consistent candidates, for known atoms |
| hedge, hedge_slope | share of scans reserved for the no-prior order, and its change per doubling of budget |
| tilt | allocation over the stream at a fixed total: spend early or late |
| rotate | share of scans on a slice further down the order, moved every task |

The champion (cold-start pair prior, half hedged) is the default vector. The
simulator is exact and fast: `tests/test_growth_coach.py` reproduces the
audited static, blind, warm, hedged and revealed arms hit for hit against a
port of the original loop with full sorts, and checks every window against
`np.lexsort` and `interleave`. Scores are built as a table over atom pairs and
windows are recomputed only when the evidence or the allotted scans change:
tens to hundreds of times faster than the original arms for the champion, and
several times faster for coaches whose evidence changes every task.

## 2. Screen 1: seven levers, hedge held at one half

`mechanism_coach_screen.py`, `analysis/mechanism-coach-screen-20260922.json`.
In-sample optimum by cross-entropy search (24 × 10) on the 32 worlds it is
scored on, an upper bound on what training could buy there. Rule fixed before
the run: proceed only if the optimum's share of the champion-to-ceiling gap is
at least 0.10 at four of six budgets and positive at all six.

| budget | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- |
| champion | 293 | 584 | 733 | 1011 | 1505 | 2001 |
| in-sample optimum | 398 | 581 | 911 | 1290 | 1763 | 2256 |
| revealed ceiling | 1743 | 2644 | 2641 | 2608 | 2560 | 2522 |
| share of gap | 0.072 | **-0.001** | 0.093 | 0.175 | 0.245 | 0.489 |

**Did not pass.** Soft retention is harmful at every setting tried; count
evidence at 0.5 is the best single lever. The optimum, fitted on in-support
worlds only, is also better than the champion on the 16 new-family worlds at
every budget (+20 to +162 of 1600).

## 3. Screen 2: the hedge and allocation made searchable

`mechanism_coach_screen2.py`, `analysis/mechanism-coach-screen2-20260923.json`.
The first screen's fixed arms showed the hedge binding at tight budgets (the
unhedged prior solves 479 against the champion's 293 at 128), so the hedge
share, its slope in log budget, and the allocation tilt were added, and the
optimum was taken over in-support and new-family worlds together, each
normalised by its own gap. Same worlds; the first screen's champion, warm and
revealed totals were asserted equal under the new code. Rule: as before on the
in-support worlds, plus non-negative at every budget out of support.

| share of gap | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- |
| in support | 0.078 | **0.011** | 0.067 | 0.209 | 0.371 | 0.808 |
| new family | 0.034 | 0.047 | 0.062 | 0.145 | 0.281 | 0.575 |

**Did not pass**, at the same place. The optimum front-loads the budget as far
as it is allowed (tilt 0.95), leaves the hedge at 0.48 with no slope, and uses
count 0.67, affinity 1.23, depth-one bonus 1.16, pick 0.50. At 4096 it solves
2422 of the ceiling's 2522. At 256 no arm in either screen is more than about
0.02 of the gap above the champion.

## 4. Why the tight budgets do not move

**The window rarely holds evidence.** At 256 no in-support world fails to take
off (median 15 of 100), but worlds plateau: a consistent candidate is in the
window on a small fraction of tasks, and every lever above acts on evidence
the agent does not have.

**The scan has no side channel** (`mechanism_near_miss_probe.py`). Of the atoms
of rows in the champion's first window, the share that belong to the world:

| outcome of the row on the visible examples | 128 | 256 | 512 | 1024 |
| --- | --- | --- | --- | --- |
| consistent | 0.787 | 0.793 | 0.711 | 0.681 |
| fits every positive, admits a negative | 0.086 | 0.066 | 0.062 | 0.062 |
| excludes every negative, misses a positive | 0.075 | 0.066 | 0.069 | 0.065 |
| neither | 0.070 | 0.063 | 0.065 | 0.069 |
| the window as a whole | 0.072 | 0.064 | 0.065 | 0.069 |

In-support worlds; new-family worlds are the same. Near-misses carry nothing,
and ranking atoms by accumulated near-miss counts recovers the world's atoms no
better than window frequency.

**Rotating the window does not help** (`mechanism_rotation_probe.py`). A
quarter of the scans on a moving slice: -0.012 and -0.026 of the gap at 128
and 256; half: -0.60 at 4096.

**The prior saturates** (`mechanism_prior_scaling.py`). The champion with its
prior fitted on 25 to 6400 handed training worlds, 32 held-out worlds per split,
mean tasks solved of 100:

| seen triple | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- |
| no prior | 1.9 | 3.3 | 4.5 | 16.2 | 34.8 | 54.5 |
| 25 worlds | 7.8 | 13.4 | 24.6 | 37.6 | 50.0 | 62.5 |
| 100 | 12.3 | 19.7 | 27.2 | 39.7 | 52.7 | 64.8 |
| 400 | 14.0 | 21.2 | 27.1 | 38.4 | 55.7 | 67.9 |
| 1600 | 15.0 | 20.9 | 26.5 | 37.7 | 56.9 | 67.3 |
| 6400 | 14.9 | 22.2 | 27.5 | 37.3 | 57.5 | 66.6 |
| prior from unstructured worlds, 6400 | 10.4 | 18.9 | 25.4 | 32.7 | 42.8 | 58.7 |
| revealed ceiling | 50.3 | 80.7 | 82.6 | 81.3 | 80.2 | 79.2 |

Every step from 400 to 6400 worlds is within noise at every budget, on
untrained family combinations as well. Most of what the prior buys is generic:
a prior from worlds with no family structure gets 10.4 of the structured 14.9
at 128. The tight-budget limit is the **form** of the pair prior, not its data.

Together: no policy over the loop's evidence, trained or tuned, can cross the
tight-budget gap, and more cross-world experience in the present form will not
either. What would is a representation of worlds that says more before the
first solve than which atoms are common.

## 5. A correction to rule 6

The hedge rule ("reserve half the scan budget; it costs nothing in support")
rests on +121 [26, 213] on new-family worlds at budget 1024. At budget 4096 the
half-hedged prior loses to no prior on new-family worlds: -224 [-363, -97] at
400 training worlds and -237 [-386, -103] at 6400
(`mechanism-prior-scaling-20260923.json`). The hedge keeps its promise, which
is a bound: the hedged agent (43.2 of 100) stays above the no-prior agent at
half the budget (30.7). But "turns the out-of-support failure into a gain" was
read at one budget, which is the error rule 8 exists to prevent.

## 6. The RL-trained coach (development)

`mechanism_coach_dev.py`, `analysis/mechanism-coach-dev-20260923.json`, fresh
seed 621101. Evolution-strategies policy search (8 antithetic pairs, common
random numbers, centred ranks per budget and per kind of lifetime), started at
the champion, 40 generations, each on 8 worlds never lived in before: 30,720
training lifetimes. A quarter of them are **practice at unfamiliarity**: a
world containing one training family, lived with a prior fitted on the
training worlds without that family. Controls on the same lifetimes: random
search (160 perturbed champions, the best by the same shaped fitness), six
per-budget coaches (the capacity arm), and the same training with practice
replaced by in-support lifetimes. 32 held-out worlds per split, 7,013 s.

It learned a sensible policy: hedge 0.25 + 0.17·log2(B/1024), which is none at
128-256 and 0.62 at 4096; tilt 0.73; count 0.57; affinity 0.50; pick 0.22;
depth-one penalty 1.1. Coach at generation 40 minus champion, tasks of 3,200:

| split | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- |
| seen combination | +12 [-37, 64] | +78 [-52, 221] | +247 [39, 470] | +433 [260, 609] | +384 [257, 510] | +410 [310, 517] |
| new combination | -30 [-92, 29] | -48 [-137, 43] | +115 [-51, 296] | **+311 [147, 481]** | **+488 [325, 657]** | **+323 [214, 437]** |
| new family | -33 [-80, 11] | **-66 [-119, -10]** | **-124 [-208, -51]** | -119 [-251, 2] | +76 [-136, 277] | **+430 [289, 572]** |

On trained combinations at 4096 it solves 74.6 of 100 against a ceiling of
77.7. The checkpoint curve rises in support (+175, +174, +317, +433 at 1024
for generations 5, 10, 20, 40) and is not monotone out of support.

What the controls say:

- **Random search does as well in support**: the coach minus random search has
  an interval containing zero at 11 of 12 budget-split cells on seen and new
  combinations, and at 4096 on new combinations random search is better by
  83 [14, 155]. The gain is from searching policies on lifetimes, not from the
  gradient-following update.
- **Random search is unsafe out of support.** It chose a hedge of 0.42 at 128
  falling to none at 4096 and loses 724 [532, 930] to the champion on new-family
  worlds at 4096; the ES coach beats it there by 1,154. Best-of-160 on 32
  lifetimes each picked a candidate that fit its sample.
- **Practice at unfamiliarity is what buys robustness**: coach minus the
  no-practice coach on new-family worlds is +19, +33, +49, +214, +228, +142,
  five of six intervals entirely positive, and indistinguishable in support.
- The per-budget capacity arm matches the shared coach in support except at
  128 on new combinations (per-budget better by 114 [55, 178]), and is better
  on new-family worlds at 1024-2048 (by 194 and 296).
- ~~Out-of-support behaviour is fragile: generation 10 lost 748 on new-family
  worlds at 4096.~~ **Withdrawn (§9):** that checkpoint had soft retention
  0.011 and the simulator bug dropped its hedge. Re-scored it loses
  -114 [-242, 16] there, and still -151 [-261, -46] at 1024.

So the component does what was asked where the loop receives evidence, and it
is not reliable: it loses significantly at mid budgets on worlds with an
untrained family. §7 repeats it inside a fixed safety contract.

## 7. The coach inside a safety contract (development)

`mechanism_coach_guarded_dev.py`, `analysis/mechanism-coach-guarded-dev-20260923.json`,
fresh seed 624101. The hedge share is fixed at one half and the hedged half
always follows the fixed no-prior rule, whatever the coach says
(`arm='guarded'`); ES trains the other eight fields, same procedure. Trained
coach: count 0.58, affinity 0.69, pick 0.45, tilt 0.81, unknown 1.25,
depth-one -0.07. Minus champion, tasks of 3,200:

| split | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- |
| seen combination | +11 [-40, 66] | +170 [81, 268] | +171 [31, 324] | +270 [171, 375] | +173 [46, 311] | +268 [132, 436] |
| new combination | -2 [-38, 36] | **-106 [-155, -58]** | -14 [-98, 68] | +171 [66, 275] | +219 [112, 331] | +318 [214, 423] |
| new family | +24 [-2, 55] | -6 [-45, 33] | +45 [-21, 114] | +138 [64, 219] | +269 [176, 370] | +142 [-38, 294] |

The guard makes it safe on worlds with an untrained family, and it loses at 256
on untrained combinations, more with training (+9, -36, -106 at generations
10, 20, 40). The control that matters is the **same parameters without the
guard**, hedge share still one half:

| split | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- |
| seen combination | +46 [-10, 109] | +207 [119, 307] | +268 [142, 399] | +388 [248, 525] | +400 [260, 539] | +361 [218, 529] |
| new combination | +10 [-37, 56] | -23 [-88, 46] | +31 [-69, 130] | +300 [162, 439] | +456 [317, 590] | +442 [346, 544] |
| new family | +39 [10, 71] | +8 [-44, 56] | +35 [-49, 117] | +176 [34, 320] | +338 [196, 479] | +289 [59, 488] |

No interval entirely negative anywhere, and every cell from 1024 up entirely
positive on every split. Safety came from holding the hedge share, not from
constraining the hedged order. ES beat random search at matched lifetimes in
16 of 18 cells in this run (random search chose count -0.71). That arm was a
control, trained under a constraint it was not scored under, so §8 trains that
procedure directly on fresh seeds before anything is predeclared.

## 8. The coach with the hedge share fixed (development)

`mechanism_coach_fixed_hedge_dev.py`, `analysis/mechanism-coach-fixed-hedge-dev-20260923.json`,
fresh seed 625101. Hedge share one half, every other field trained, no guard.
Trained coach: count 0.71, affinity 0.40, tilt 0.57, pick 0.14. Minus champion:

| split | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- |
| seen combination | -20 [-90, 60] | +18 [-90, 142] | +191 [10, 386] | +351 [208, 504] | +361 [241, 479] | +260 [194, 329] |
| new combination | **-96 [-169, -29]** | -105 [-240, 44] | +255 [57, 478] | +519 [362, 679] | +486 [363, 604] | +270 [167, 374] |
| new family | -13 [-59, 33] | +6 [-57, 72] | +32 [-60, 128] | +269 [133, 415] | +229 [42, 420] | +221 [99, 345] |

Every cell from 1024 up improves, on every split, and on new-family worlds
nothing is lost anywhere. One cell fails: 128 on untrained combinations, and
the loss grows with training (-11, -44, -96 at generations 10, 20, 40).

**The ablation** (`mechanism_coach_ablation.py`, same worlds, the dev run
reproduced to the task) resets one lever at a time. Resetting the weight on
repeated evidence alone removes the loss: 0 [-54, 53]. In support, a row the
agent keeps picking is usually right, and trusting repetition pays; under a
combination shift the agent keeps picking the same wrong rows, and the weight
entrenches them. The coach learned this from lifetimes in which the prior was
never wrong about a combination. Resetting the allocation tilt makes the loss
larger (-124), so front-loading is not the cause.

The same ablation shows how sensitive a life is to small parameter changes:
moving the depth-one weight from -0.05 to 0 shifts totals at 256 by up to 80
tasks. The intervals above are over worlds for a fixed coach; they do not
include that sensitivity.

## 9. A simulator bug, found by the audit, and what it changed

The confirmation audit's replay check (§11) found that `Simulator.lifetime`
credited soft evidence through a local named `share`, which is also the hedge
share. A coach with soft retention above zero therefore dropped its hedge to
soft/n after its first window with several consistent candidates. The bug
entered with the hedge-slope refactor before screen 2, so screen 1 is
untouched (its soft arms re-score identically). Fixed; the regression test
`test_soft_retention_keeps_the_hedge` fails on the old code and passes on the
new. Every evaluated arm with soft above zero was re-scored on its own held-out
worlds, with the champion reproducing its stored totals exactly
(`mechanism_coach_rescore.py`, `analysis/mechanism-coach-rescore-20260923.json`):

| arm | split, budget | before | after |
| --- | --- | --- | --- |
| dev run 1, generation 10 | new family, 4096 | -748 | -114 [-242, 16] |
| dev run 1, generation 10 | new family, 1024 | -301 | -151 [-261, -46] |
| practice run, both kinds, generation 40 | new family, 4096 | -607 | +207 [27, 393] |
| practice run, both kinds, generation 40 | new combination, 256 | -106 | -220 [-366, -93] |
| fixed-hedge run, random search | new family, 4096 | -700 | -54 [-206, 104] |

What this withdraws: the "fragile checkpoint" of §6 (generation 10's -748 was
the bug), and the reading of the practice run that combination practice ruins
out-of-support behaviour. What survives: that generation still loses on
new-family worlds at 512-1024, and the both-kinds coach still loses at tight
budgets on untrained combinations. Every final coach used in §7, §8 and §10 had
soft retention exactly zero and is unaffected. Training itself was affected
wherever a perturbation had soft above zero, which no re-scoring repairs: the
procedure as it will run with the fix has not been run in development, so the
confirmation's dress rehearsal (§11) runs it before anything is frozen.

## 10. Practice at the unfamiliarity being scored, and high-confidence deployment (development)

`mechanism_coach_practice_dev.py` (seed 626101) trained the fixed-hedge
procedure twice on the same held-out worlds: with family practice only, and
with family and combination practice. The family-only coach at generation 40
passes every cell of the drafted gate: +275 to +476 at 1024-4096 on every
split, no significant loss at 128-512 (worst -79 [-178, 15] at 128 on untrained
combinations). Its generation-20 checkpoint does not (-190 at 128 on untrained
combinations). The both-kinds coach, after the §9 correction, loses at tight
budgets on untrained combinations (-143, -220). Combination practice as a
training signal did not help.

What did: using the practice kinds for **validation** rather than training
(`mechanism_coach_validation_gate.py`, `analysis/mechanism-coach-validation-gate-v2-20260923.json`).
After training, coach and champion live 32 fresh worlds of each kind:
in-support, a training family with a prior fitted without it, and a training
combination with a prior fitted without it. The coach is deployed at a budget
only if its paired interval is entirely above zero in every kind; elsewhere the
agent runs the champion. Retrospectively, on both fixed-hedge coaches, the rule
deploys at 1024, 2048 and 4096 and falls back at 128-512, and the deployed
policy then passes every cell of the drafted gate on both seeds' held-out
worlds. A looser pooled rule (v1) deployed at 256-512 too and would have let
through -105 at 256. The scope of the claim is now set by this procedure, not
chosen by the experimenter.

## 11. The confirmation: failed as frozen

`EXPERIMENT-mechanism-coach-confirmation.md`, frozen 2026-09-23 with the
SHA-256 of runner, simulator, reference and audit;
`mechanism_coach_confirmation.py`, `analysis/mechanism-coach-confirmation-20260923.json`,
journals in `runs/mechanism-coach-confirmation-20260923/`. Before freezing, the
runner ran unchanged at full size on development seed 627101
(`mechanism_coach_rehearsal.py`): its audit passed, and it failed one
improvement cell at 48 worlds per split (+140 [-14, 288]), so the sample was
raised to 128 worlds per split from the rehearsal's per-world effects with the
criterion unchanged. Seeds 951101 and 952101, 3,693 s.

**The claim failed in both replications, and not where it was expected to.**
The gated arm is the *deployed* policy. Validation deployed the coach at 4096
only in replication A and at 512, 1024 and 4096 in replication B, so the
improvement cells at 1024 and 2048 (A) and 2048 (B) read the champion against
itself: zero.

The trained coach's own contrasts are reported beside the gate and are not
gated. Tasks of 12,800 per split (128 worlds of 100):

| replication | split | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | seen combination | -94 [-220, 37] | -45 [-251, 164] | +561 [275, 852] | +1786 [1489, 2084] | +1654 [1378, 1930] | +1393 [1197, 1600] |
| A | new combination | -64 [-190, 58] | -45 [-197, 103] | +132 [-34, 302] | +1255 [979, 1535] | +2165 [1900, 2423] | +1777 [1563, 2003] |
| A | new family | +81 [-11, 175] | +194 [75, 311] | +225 [51, 400] | +1042 [780, 1315] | +1468 [1158, 1781] | +1579 [1299, 1864] |
| B | seen combination | +212 [90, 339] | +94 [-44, 233] | +481 [271, 691] | +1467 [1170, 1764] | +1653 [1402, 1905] | +1356 [1160, 1558] |
| B | new combination | +26 [-85, 138] | +177 [53, 304] | +484 [288, 683] | +1400 [1110, 1681] | +1456 [1147, 1759] | +1134 [914, 1349] |
| B | new family | +126 [50, 205] | +132 [37, 237] | +269 [97, 442] | +664 [423, 906] | +909 [602, 1217] | +1389 [1101, 1673] |

Every improvement cell has its interval far above zero and no cell has one
entirely below zero, in both replications. Per world of 100 tasks on worlds of
an untrained family, the trained coach solves 27.7 against the champion's 19.5
at budget 1024 and 63.3 against 51.0 at 4096 (replication A).

**The deployment layer is what failed.** In every budget it abstained where the
coach was clearly better, the validation kind that fell short was the
family-shift one: 32 worlds gave +59 (lower bound -9) and +58 (-36) at 1024 and
2048 in A, and +56 (-29) at 2048 in B. That kind is the noisiest and, on this
evidence, the most pessimistic proxy for held-out unfamiliar families.
Requiring significance in every one of three 32-world kinds had too little
power at the budgets where the effect is merely large.

The independent audit passed (`analysis/audit-mechanism-coach-confirmation-20260923.json`):
journal hashes, deployment decisions recomputed from validation totals, every
total, contrast and gate recomputed from the journals, all 373,774 picks
checked against constraints rebuilt from the example strings, 6,000 through
the host interpreter (27 graded misses the interpreter accepts, the known
conservative direction; none the other way), no tested mechanism in any
prior's solved set, and 48 lifetimes replayed decision for decision by the
full-sort reference.

What this licenses, stated plainly: **C-coach is not confirmed.** The trained
coach's clean record across 36 cells in two replications is a description of a
reported, ungated arm, and turning it into a claim now would be choosing the
arm after seeing the results. It is strong evidence for what to predeclare
next: the trained coach itself, or the same deployment rule with validation
sized from these runs' per-kind variances, on fresh seeds.

## 12. The second coach confirmation: failed, and the line is closed

`EXPERIMENT-mechanism-coach-confirmation-2.md`: the byte-identical runner with
one constant changed, validation worlds per kind 32 → 256, sized from the first
confirmation; seeds 961101 and 962101; the protocol said in advance that a
failure ends this line. With the larger validation the rule deployed the coach
at 256-4096 in both replications. Every improvement cell passed in both, but in
replication A the deployed coach lost at 256 on untrained combinations,
-328 [-499, -158], and replication B was close (-122 [-290, 40]). The
validation kind built to anticipate that shift (a training combination lived
with a prior fitted without it) passed at 256 while the held-out untrained
combinations lost. This is the failure the ablation of §8 located: trusting
repeated evidence entrenches wrong rows when the prior is wrong about a
combination, and a simulated shift from training material underestimates it.
The audit passed (`analysis/audit-mechanism-coach-confirmation2-20260923.json`:
389,257 picks, 48 replayed lifetimes), so the failure is the procedure's, not
the measurement's. **C-coach is not confirmed, and no third run will be
predeclared.**

## 13. The tight-budget wall moves: a family-level world model (development)

**The wall is not a property of the generator**
(`mechanism_oracle_structure_probe.py`, seed 628101, 32 in-support worlds).
Told which three families its world is drawn from, the earned loop solves
18.0, 35.4, 50.4 and 66.8 of 100 at budgets 128-1024, against the champion's
11.8, 18.2, 25.6 and 35.0. Told the 14 keys it solves as much as the revealed
ceiling. So §4's conclusion was half right: no *policy* over the loop's
evidence crosses the wall, but a better *representation* could.

**A posterior over family triples recovers much of it** (`rsi/family_inference.py`).
The agent keeps P(triple | families of the atoms it has evidence for), with a
slip rate for wrong picks, and adds 2 × log(1e-4 + P(atom's family is in the
world)) to each atom's score. Four development runs:

| run | prior over triples | what it showed |
| --- | --- | --- |
| `mechanism_family_inference_probe.py`, seed 628101 | training frequencies | in support, unhedged: +204 to +555 of 3,200 at 128-1024, about half the oracle's gain |
| `mechanism_family_inference_support.py`, seed 629101 | training frequencies | hurts on untrained combinations at 256 (-66; -67 [-119, -18] hedged): an untrained triple starts at 1/16 the weight of trained ones |
| `mechanism_family_inference_uniform.py`, seed 629101 | uniform | fixes it: +145 to +389 on untrained combinations at every budget; the learned sloped hedge leaves about -2 tasks per world at 512 on untrained-family worlds |
| `mechanism_family_inference_replication.py`, seed 630101 | uniform | replicates, sloped hedge: every trained- and untrained-combination cell positive, untrained family n.s. everywhere |
| `mechanism_family_inference_step.py`, seed 631101, 64 worlds | uniform, no hedge at 128-256, half from 512 | untrained combinations +411 to +986 of 6,400 at every budget; trained combinations positive everywhere, significant except 512 (+147 [-23, 327]); untrained family no loss anywhere, +112 at 128, +209 to +611 from 1024 |

On the last seed, at budget 256, the family agent solves 24.3 against 19.1 of
100 on trained combinations and 31.5 against 21.0 on untrained ones. The
configuration was chosen across the first three seeds and checked unchanged on
the fourth; it is predeclared in `EXPERIMENT-mechanism-family-confirmation.md`
(§14). `tests/test_family_inference.py` holds the fast agent to a full-sort
reference, `rsi/family_reference.py`, pick for pick.

What it is and is not: a written representation, not a learned one. The family
labels are syntax the agent reads from the programs it scans; the uniform prior
learns nothing about which families occur together; all world-specific
knowledge comes from the agent's own evidence within the world. The oracle is
still about twice as good at 256, so inference recovers roughly half of what
the representation could give.

## 14. C-family: confirmed

`EXPERIMENT-mechanism-family-confirmation.md`, frozen 2026-09-23 with the
SHA-256 of runner, family model, simulator, reference and audit;
`mechanism_family_confirmation.py`, `analysis/mechanism-family-confirmation-20260923.json`,
journals in `runs/mechanism-family-confirmation-20260923/`. Seeds 971101 and
972101, 128 held-out worlds per split, 1,928 s. **Both replications passed
every one of their 18 cells.** Family agent minus champion, tasks of 12,800:

| replication | split | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | trained combinations | +643 [459, 838] | +965 [684, 1259] | +554 [264, 851] | +1398 [1097, 1708] | +1171 [939, 1402] | +697 [517, 887] |
| A | untrained combinations | +932 [723, 1151] | +677 [463, 902] | +248 [37, 461] | +1059 [802, 1327] | +1376 [1114, 1637] | +759 [601, 916] |
| A | untrained family | +253 [149, 362] | +27 [-95, 144] | +101 [13, 191] | +233 [133, 338] | +531 [305, 766] | +1189 [948, 1436] |
| B | trained combinations | +1056 [838, 1284] | +1346 [992, 1701] | +598 [289, 914] | +1437 [1135, 1757] | +1374 [1111, 1629] | +706 [551, 865] |
| B | untrained combinations | +1177 [969, 1399] | +1338 [963, 1740] | +722 [403, 1067] | +1546 [1222, 1883] | +1635 [1361, 1912] | +1096 [921, 1274] |
| B | untrained family | +278 [179, 378] | -56 [-178, 68] | +153 [58, 260] | +383 [248, 527] | +864 [657, 1085] | +1370 [1122, 1621] |

Per world of 100 tasks on untrained combinations, the family agent solves 15.7
and 16.5 against the champion's 8.4 and 7.4 at budget 128, and 22.5 and 25.5
against 17.2 and 15.0 at 256. On worlds of a family no training world held it
does no harm at any budget and gains at five of six.

The independent audit passed (`analysis/audit-mechanism-family-confirmation-20260923.json`):
journal hashes, every total, contrast and gate recomputed from the journals,
all 381,853 picks checked against constraints rebuilt from the example strings,
6,000 through the host interpreter (38 graded misses the interpreter accepts,
the known conservative direction; none the other way), no tested mechanism in
the prior's solved set, and 48 lifetimes of both arms replayed decision for
decision by the full-sort reference.

**What C-family is.** The first predeclared, audited result in this repository
in which the earned loop, with every unit of its experience earned, acquires
worlds it has never seen faster at the tight budgets nothing else moved, across
a combination boundary, and without harm across a family boundary. It is a
representation result: the gain comes from reasoning about which families a
world uses from the agent's own evidence, and it rests on family labels being
readable from the programs scanned. It is not a learning-to-learn result and
it does not make the RL coach's gains confirmed.

## 16. The grouping learned from worlds: C-growth confirmed, C-learned failed by one cell

C-family read each atom's family from its program text. `rsi/learned_groups.py`
learns a grouping instead, from which atoms appear together across training
worlds: spectral clustering of positive PMI of co-occurrence, the number of
groups chosen by held-out world likelihood. Development
(`analysis/mechanism-learned-groups-*.json`): recovery of the true families
rises with experience (adjusted Rand 0.15, 0.84, 0.89, 0.89 at 100, 400, 1600,
6400 worlds); the eigengap merged small families and lost at 256 on
untrained-family worlds; likelihood selection (5-6 groups) matched the
syntactic agent on two seeds, the second untouched.

`EXPERIMENT-mechanism-learned-confirmation.md`, committed (`515d109`) before
the run, seeds 981101 and 982101, 1,456 s. The learned agent uses groups from
1,600 training worlds; the `early` agent the same method on the first 400; the
champion's pair prior comes from the first 400 in every arm. Learned agent
minus champion, tasks of 12,800:

| replication | split | 128 | 256 | 512 | 1024 | 2048 | 4096 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | trained combinations | +818 [638, 1012] | +840 [583, 1106] | +253 [25, 487] | +1027 [778, 1282] | +1224 [995, 1457] | +660 [485, 842] |
| A | untrained combinations | +704 [563, 852] | +654 [456, 850] | **+153 [-59, 367]** | +961 [676, 1256] | +1340 [1048, 1631] | +1015 [795, 1229] |
| A | untrained family | +232 [129, 339] | +11 [-119, 141] | -28 [-125, 68] | +71 [-23, 169] | +337 [175, 511] | +1001 [809, 1197] |
| B | trained combinations | +935 [721, 1158] | +896 [613, 1188] | +484 [206, 769] | +1218 [935, 1502] | +1331 [1124, 1532] | +757 [611, 903] |
| B | untrained combinations | +1406 [1154, 1677] | +1216 [955, 1484] | +266 [43, 492] | +1426 [1151, 1712] | +2168 [1906, 2426] | +1166 [992, 1341] |
| B | untrained family | +342 [247, 439] | -28 [-138, 83] | +105 [3, 211] | +245 [131, 365] | +497 [317, 685] | +790 [597, 991] |

**C-learned failed**, on the one cell the protocol named as likely to: untrained
combinations at 512 in replication A. Replication B passed all 18 cells, and no
safety cell in either replication came near failing. It is reported as a
failure; the gate is not revisited.

**C-growth passed in both replications**: summed over all 18 cells, the agent
on groups from 1,600 worlds solves +6,993 [5,890, 8,110] and +8,077
[6,932, 9,264] more tasks than the same agent on groups from 400 worlds. The
groups from 400 worlds (four of them) hurt in places, for example -354 and -237
at 512 on untrained combinations and -115 and -143 at 256 on untrained-family
worlds; the groups from 1,600 (six) turn those around.

The independent audit passed (`analysis/audit-mechanism-learned-confirmation-20260923.json`):
both groupings relearned from the recorded training worlds equal the recorded
labels; every total, contrast, growth figure and gate recomputes from the
journals; all 555,560 picks check against constraints rebuilt from the example
strings; 6,000 sampled picks through the host interpreter (24 graded misses
it accepts, the known conservative direction, none the other way); no tested
mechanism among training solved sets; 54 lifetimes of the three arms replayed
decision for decision by the full-sort reference.

**What C-growth is.** The first predeclared, audited result in this repository
in which an agent's ability to acquire worlds it has never seen, at every
resource level taken together, improves with its experience of other worlds
through a structure it learned from that experience, and keeps improving past
the point where the cross-world pair prior stopped (about 400 worlds). The
grouping is learned without labels, from co-occurrence alone. What is not
claimed: that the learned agent beats the champion in every cell (C-learned
failed by one), or that the within-world learner itself improves; it is a
fixed rule throughout.

## 15. Files

`rsi/growth_coach.py`, `tests/test_growth_coach.py`; `mechanism_coach_screen.py`,
`mechanism_coach_screen2.py`, `mechanism_near_miss_probe.py`,
`mechanism_rotation_probe.py`, `mechanism_prior_scaling.py`,
`mechanism_coach_dev.py`; analyses of the same names dated 2026-09-22/23;
logs in `runs/coach/`.
