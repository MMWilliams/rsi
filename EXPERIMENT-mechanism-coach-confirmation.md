# Predeclaration: a coach trained on lifetimes, confirmatory run

Written 2026-09-23, before the confirmatory seeds are drawn. Development
evidence: `COACH-RESULTS-2026-09-23.md` and the analyses it names, including the
dress rehearsal of this exact runner on development seed 627101
(`analysis/mechanism-coach-rehearsal-20260923.json` and its audit, which
passed). Every threshold, arm, split and statistic below is fixed here; the
run reports them whether they pass or fail.

## 1. The claim

An external component (the *coach*, `rsi/growth_coach.py`) sets the free
choices of the earned loop: how far rows built from unevidenced atoms are
pushed down, the weights on the cross-world pair prior, on repeated evidence
and on the conditional prior, a depth-one bonus, soft retention, a preference
among consistent candidates for known atoms, and the allocation of a fixed
total budget over the task stream. It is trained by evolution-strategies
policy search on the return of whole lifetimes (tasks solved), continually,
starting from the champion, with a quarter of its lifetimes spent practising a
withheld family. The hedge share is held at one half and is not trained.

After training it is **deployed with high confidence**: coach and champion live
fresh validation worlds of three kinds built from training material alone
(in-support; a training family lived with a prior fitted without that family;
a training combination lived with a prior fitted without that combination),
and at each budget the agent runs the coach only if the coach's paired
interval is entirely above zero in every kind, and the champion otherwise.

**C-coach.** The deployed policy makes the earned loop solve more tasks than
the champion on worlds it never lived in at every budget where the loop
receives evidence (1024, 2048 and 4096 scans per task), and is not
significantly worse at any budget (128, 256, 512), on worlds of trained family
combinations, of untrained combinations, and of an untrained family.

The budget split was found in development (two in-sample screens: headroom at
most 0.093 of the gap to the informed ceiling at 128-512 and at least 0.175
from 1024 up; four measurements put the tight-budget limit down to information
the loop does not receive). In the procedure it is not chosen by anyone: the
deployment rule decides per budget from validation lifetimes. The gate reads
every budget. At budgets where the procedure abstains, the claim is only that
it does no harm, and it holds there by construction; that is said here so that
it is not mistaken for evidence.

## 2. Procedure

`mechanism_coach_confirmation.py`, whose constants this quotes: 400 prior
training worlds with 64 solved mechanisms each; seven family-practice priors
and one combination prior per training combination, each fitted on the
training worlds without it; ES over `unknown, pair, count, depth1, affinity,
soft, pick, tilt` with sigmas 0.2, 0.2, 0.25, 1.0, 0.25, 0.2, 0.25, 0.2, eight
antithetic pairs, learning rate 1, 40 generations, each on 6 in-support and 2
family-practice worlds never lived in before; hedge share 0.5, slope 0;
`arm='earned'`. Validation: 32 worlds per kind, paired bootstrap per kind,
20,000 resamples. Streams of 100 tasks. Families `popcount` and `xormod` are in
no training, practice or validation world; 20% of the other family
combinations are withheld from training and validation.

## 3. Evaluation

Per replication, 128 held-out worlds in each of `seen_triple`, `new_triple`,
`new_family`, never lived in by the coach, their streams removed from every
prior's solved set. Champion and trained coach each live every world once at
each budget; the deployed policy's decisions at a budget are the coach's where
deployed and the champion's elsewhere. Paired over worlds, 20,000 bootstrap
resamples; the interval is the 2.5 and 97.5 percentiles of the resampled sum of
deployed policy minus champion. The trained coach's own contrasts are reported
beside it and are not gated.

## 4. Gate

A replication passes if, on each of the three splits:

- **improve**: at 1024, 2048 and 4096 the interval is entirely above zero;
- **safe**: at 128, 256 and 512 the interval is not entirely below zero.

Nine improvement cells and nine safety cells per replication. The claim passes
only if both replications pass. "Safe" is no significant loss, not
non-inferiority to a margin.

**Sample size.** The rehearsal used 48 worlds per split and failed one
improvement cell, untrained combinations at 4096: +140 [-14, 288], where the
champion is already strong and the per-world effect is smallest (2.9 tasks,
standard deviation 11.3). The criterion is unchanged; the number of worlds was
raised to 128 per split, chosen from the rehearsal's per-world effects so that
the weakest improvement cell has an expected z of 2.9 (about 83% power) and
every other cell more. The rehearsal's other eight improvement cells had
intervals entirely above zero at 48 worlds.

## 5. Audit

`audit_mechanism_coach_confirmation.py`: catalog digest and journal hashes;
the deployment decision recomputed from the recorded validation totals; every
total, contrast and gate recomputed from the journal; every pick checked
against constraints rebuilt from the example strings; 3,000 sampled picks
through the host interpreter; no tested mechanism in any prior's solved set;
and sampled lifetimes of both arms replayed decision for decision by
`rsi/coach_reference.py`, which sorts the whole catalog for every task. That
replay is the check that found the simulator bug of §9 of the results.

## 6. What a pass would and would not mean

A pass would be the first result in this repository in which a component
trained on the lifetimes of other worlds improves how fast an agent acquires
worlds it has never seen, with every unit of the agent's experience earned,
reliably across the resource range and across a family boundary, because it
was deployed only where it could show it helps.

It would not show that the reinforcement-learning update matters (random
search at matched lifetimes was mixed against it in development). It would not
move the tight-budget wall, which development says is informational; there the
procedure abstains. One environment, one task form, one hypothesis language.

Replication seeds: A 951101, B 952101.

Frozen: 2026-09-23. SHA-256: runner `mechanism_coach_confirmation.py` 94cbafd95dc7266ab6bd9735ac2065182cfde22aaff695ceada4263bed59f1cc; simulator `rsi/growth_coach.py` bb22f9a0193258b8e3bc9c94f766ee639d76ce5aaa683f9aba996f5ed61af868; reference `rsi/coach_reference.py` 9a8e972e94cb70d117cfb7b3ef0c42ed3f0c38b2cf2f5f2c35243a563603d3ef; audit `audit_mechanism_coach_confirmation.py` f3e334c92b604ccbcb69ceff743477e614cc9a26d5faf6ca21dc3e16a0dd4deb.
