# Predeclaration: the coach confirmation, second run

Written 2026-09-23, after the first confirmation failed and before these seeds
are drawn. This is the second predeclared confirmation of this line of work,
and it is said here so that nobody counts it as the first.

## What happened to the first

`EXPERIMENT-mechanism-coach-confirmation.md` failed as frozen
(`COACH-RESULTS-2026-09-23.md` §11, audit passed). The gated arm was the
deployed policy, and the high-confidence deployment step abstained at budgets
where the trained coach was clearly better: at 1024 and 2048 in replication A
and at 2048 in B. In each case the validation kind short of significance was
the family-shift one, with 32 worlds. The trained coach itself, reported and
not gated, had every improvement interval far above zero and no interval
entirely below zero at 128-512, in both replications. The first confirmation is
now development evidence for this one.

## What changes, and what does not

Exactly one constant of the procedure: validation worlds per kind, 32 → 256.
The size comes from the per-world validation effects and standard deviations
pooled over the first confirmation's two replications and its rehearsal (96
worlds per kind): at 256 the weakest kind at 1024-4096 (family shift) has an
expected z of 5.5 or more, where at 32 it had about 2.

Unchanged: the claim C-coach, the training procedure, the deployment rule
(deploy at a budget iff the paired interval is entirely above zero in every
kind), the gated arm (the deployed policy), the three splits, 128 evaluation
worlds per split, the nine improvement cells (1024, 2048, 4096) and nine safety
cells (128, 256, 512) per replication, both replications required, and the
audit. The runner `mechanism_coach_confirmation.py` is byte-identical to the
one frozen in the first protocol; `mechanism_coach_confirmation2.py` only sets
the output paths, the seeds and the validation size before calling it.

Everything in §1-6 of the first protocol applies as written, with 256 in place
of 32 in §2. At budgets where the rule abstains, the safety cells hold by
construction and are not evidence; at 128-256 the combination-shift kind is
expected to keep it abstaining (expected z about 1.3 at 256).

## What a pass would mean, and what a failure would

A pass confirms C-coach: an RL-trained component, deployed only where it can
show a confident gain on validation lifetimes built from training material,
reliably improves how fast the earned loop acquires worlds it never lived in,
including worlds of an untrained family, across the resource range, with every
unit of the agent's experience earned. It does not touch the tight-budget wall.

A failure ends this line of confirmation: no third run of this claim will be
predeclared on the strength of this one's ungated arms.

Replication seeds: A 961101, B 962101.

Frozen: 2026-09-23. SHA-256: runner `mechanism_coach_confirmation.py` 94cbafd95dc7266ab6bd9735ac2065182cfde22aaff695ceada4263bed59f1cc; wrapper `mechanism_coach_confirmation2.py` 22fc13eafcd54ad782ee63cf8f86e6223b88ec24a96003dc33d056943822c2ce; simulator `rsi/growth_coach.py` bb22f9a0193258b8e3bc9c94f766ee639d76ce5aaa683f9aba996f5ed61af868; audit `audit_mechanism_coach_confirmation.py` f3e334c92b604ccbcb69ceff743477e614cc9a26d5faf6ca21dc3e16a0dd4deb.
