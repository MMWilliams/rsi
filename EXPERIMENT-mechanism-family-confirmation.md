# Predeclaration: a family-level world model moves the tight-budget wall

Written 2026-09-23, before the confirmatory seeds are drawn. Every threshold,
arm, split and statistic below is fixed here; the run reports them whether they
pass or fail. Development evidence: `COACH-RESULTS-2026-09-23.md` §13 and the
analyses it names.

## 1. Background

The earned loop at tight budgets (128-512 scans per task) was the part of this
programme nothing moved: no policy over the loop's own evidence, trained or
tuned in-sample, recovered more than about 2% of the gap to the informed
ceiling at budget 256, and the learned pair prior stopped improving at about
400 training worlds. An oracle that tells the agent which three families its
world is drawn from roughly doubles what it solves there, so the wall is not a
property of the generator.

## 2. The agent and the claim

The **family agent** (`rsi/family_inference.py`) is the champion earned loop
(cold-start pair prior from 400 training worlds, keeps the atoms of what it
submits) with one addition: a posterior over which three families the world is
drawn from, under a **uniform** prior over every triple of the nine families,
updated from the families of the atoms the agent has evidence for with slip
0.2 (a wrong pick is as likely to carry any family), entering each atom's score
as 2 × log(1e-4 + P(its family is in the world)). It hedges nothing at budgets
128 and 256 and half the scan budget, as the champion does, from 512 up. It is
fixed; nothing is trained, and the uniform prior learns nothing about which
families occur together.

**C-family.** The family agent solves more tasks than the champion on worlds it
never lived in at every budget from 128 to 4096, on worlds of trained family
combinations and of untrained combinations, and is not significantly worse at
any budget on worlds containing a family no training world held.

## 3. How the configuration was chosen

On seed 628101 the posterior with a prior from training-triple frequencies
recovered about half the oracle's gain in support. On seed 629101 that prior
hurt on untrained combinations (an untrained triple starts at a sixteenth of
the weight of trained ones), and a uniform prior fixed it; the hedge schedule
the RL coach had learned (none at 128-256, rising with budget) left a loss of
about two tasks per world at 512 on untrained-family worlds, pooled over seeds
629101 and 630101. The step rule above replaced it, chosen from those two seeds
because an unhedged prior lost out of support from 512 up on both and the
hedge cost in support and bought nothing out of it below. On a third untouched
seed, 631101, at 64 worlds per split, the configuration here gained at every
budget on untrained combinations (+411 to +986 of 6,400), at every budget but
512 on trained combinations (+147 [-23, 327] there), and lost nowhere on
untrained-family worlds (+17 to +611). Weight 2 and slip 0.2 were fixed on the
first seed and not changed.

## 4. Evaluation and gate

`mechanism_family_confirmation.py`, whose constants this quotes. Per
replication: a fresh draw of 400 prior training worlds from 80% of the family
combinations of seven families, 128 held-out worlds each of `seen_triple`
(trained combinations, fresh keys), `new_triple` (combinations withheld) and
`new_family` (a combination containing `popcount` or `xormod`, which no
training world contains), streams of 100 tasks, their mechanisms removed from
every prior's solved set. Champion and family agent each live every world once
at each of the six budgets. Paired over worlds, 20,000 bootstrap resamples; the
interval is the 2.5 and 97.5 percentiles of the resampled sum of family agent
minus champion.

A replication passes if

- **improve**: on `seen_triple` and on `new_triple`, at each of 128, 256, 512,
  1024, 2048 and 4096, the interval is entirely above zero (12 cells);
- **safe**: on `new_family`, at each of the six budgets, the interval is not
  entirely below zero (6 cells).

The claim passes only if both replications pass.

**Power.** Pooled over the three development seeds, the weakest improvement
cell is `seen_triple` at 512 with an expected z of about 3.2 at 128 worlds;
every other improvement cell is above 4.5. The pooled effect on `new_family`
at 256 is about zero, so that safety cell is expected to pass by not losing,
not by gaining.

## 5. Audit

`audit_mechanism_family_confirmation.py`: catalog digest and journal hashes;
every total, contrast and gate recomputed from the journal alone; every pick
checked against constraints rebuilt from the example strings; 3,000 sampled
picks through the host interpreter; no tested mechanism in the prior's solved
set; and sampled lifetimes of both arms replayed decision for decision by
`rsi/family_reference.py`, which sorts the whole catalog for every task
(`tests/test_family_inference.py` holds the fast agent to it).

## 6. What a pass would and would not mean

A pass would be the first predeclared result in this repository in which the
earned loop acquires unfamiliar worlds faster at the tight budgets nothing else
moved, across a combination boundary, without harm across a family boundary.
It would be a representation result, not a learning-to-learn one: the family
model is written, not trained, and what it knows about the world comes from
the agent's own evidence within each world. Its value rests on family labels
being readable from the programs the agent scans. One environment, one task
form, one hypothesis language.

A failure is reported as one; no second run of this claim will be predeclared
on the strength of its arms.

Replication seeds: A 971101, B 972101.

Frozen: 2026-09-23. SHA-256: runner `mechanism_family_confirmation.py` fdcc04d7ca9a6319ad08db51ded5218b6fa07525fedea71630a6c21f4518d9fe; family model `rsi/family_inference.py` 65535041dd581ae16a2bf4d43f16be2048829a369359009f8f6d276122520dc4; simulator `rsi/growth_coach.py` bb22f9a0193258b8e3bc9c94f766ee639d76ce5aaa683f9aba996f5ed61af868; reference `rsi/family_reference.py` c67c1240c63a4e4b66aaf23bb77ed5ea96b3bcd8f469755ba87b68548afa7414; audit `audit_mechanism_family_confirmation.py` bcd4117dd74d7deeac640366c726e671d277f1e2a05b9c78e45fc9e2a9207eff.
