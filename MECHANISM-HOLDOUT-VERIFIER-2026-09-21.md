# Verifier growth under mechanism holdout: it does not transfer

2026-09-21. Development on opened cached panels.
Source: `analysis/mechanism-holdout-verifier-20260921.json`.

## Why this was run

After the capacity-matched audits, one growth claim remained: a larger pooled
model on more verified labels is a better evaluator than the frozen base E0, by
+73 and +69 on frozen transfer panels. Every transfer result in the programme,
including that one, used fresh seeds of the same six generators. The third
external review pointed out that fresh seeds establish instance-level transfer
only, and that the definition of intelligence growth the programme has now
adopted, improvement on *unfamiliar* problems, requires mechanism-level
transfer. This is the first mechanism-level test in the programme.

## Design

For each of the six mechanism families, a 60-leaf pooled model is trained on
the other five families' source labels (two opened source panels) and scored on
the held-out family's tasks across three opened target panels, 36 banks and 288
tasks per family, paired at bank level with a 20,000-draw percentile bootstrap.
Two references on the same tasks: the frozen base evaluator E0, and an
in-distribution 60-leaf model trained on all six families.

## Result

| family | E0 | held out | in distribution | held out minus E0 | in-dist minus E0 | transfer gap |
| --- | --- | --- | --- | --- | --- | --- |
| transform | 169 | 107 | 218 | **-62**, -77 to -47 | +49 | +111, +95 to +128 |
| ast | 41 | 1 | 88 | **-40**, -52 to -29 | +47 | +87, +73 to +100 |
| novel operator | 140 | 114 | 190 | **-26**, -39 to -13 | +50 | +76, +63 to +90 |
| stack | 238 | 214 | 262 | **-24**, -40 to -8 | +24 | +48, +32 to +64 |
| mutation | 191 | 169 | 191 | **-22**, -37 to -7 | 0 | +22, +5 to +39 |
| self edit | 241 | 111 | 245 | **-130**, -149 to -111 | +4 | +134, +117 to +152 |
| **total** | **1020** | **716** | **1194** | **-304** | **+174** | **+478** |

The held-out evaluator is worse than the frozen base on every family, with
every interval entirely negative. On self-edit tasks it loses more than half of
its correct choices. On AST it selects one correct program in 288.

## Reading

The in-distribution model gains +174 over E0 across the six families. The
transfer gap, in-distribution minus held-out, is +478. Seeing a family is
therefore worth more than the entire improvement over E0; the evaluator's gain
is not a general improvement in judging candidates that happens to be measured
on these families, it *is* familiarity with these families.

**Under the definition of intelligence growth adopted this morning, the
programme has demonstrated none.** What it demonstrated, replicated and audited
is within-distribution evaluator specialization: a model that has seen a
mechanism judges candidates for that mechanism better than a smaller model that
has seen it less. On a mechanism it has not seen it is worse than the base.

**Caveat on the E0 comparison.** E0 was itself trained with all six families
present, so "held out is worse than E0" partly reflects E0's in-distribution
advantage. That does not rescue the claim. The transfer gap of +478 does not
involve E0 at all and says the same thing: the improvement is family-bound.

**Caveat on scope.** This holds out a family from training while leaving the
base ranker, candidate generator and feature representation unchanged. It is
mechanism holdout on the evaluator's training data, which is the weakest form of
the new-mechanism split the review describes. A stronger form, new generator
families the base ranker never saw, would only be harder.

## What follows

- Every transfer number in this repository is instance-level unless labelled
  otherwise. The synthesis, the measurement contract and the memory now say so.
- Any future evaluator claim must report held-out-mechanism performance beside
  in-distribution performance, and must not regress below the base on the
  held-out mechanism. That is a gate, not a limit.
- Whether larger evaluators overfit families more than smaller ones is a cheap
  and informative follow-up, `mechanism_holdout_capacity.py` at 15, 60 and 120
  leaves. If larger models regress further on held-out mechanisms, "bigger is a
  better evaluator" is itself family-bound.

## Limits

- Opened cached panels; development evidence, not a frozen confirmation.
- One base ranker, one candidate generator, one feature representation.
- The held-out model still sees five of six families and their full mix; this
  tests transfer to an unseen mechanism among familiar ones, not to an unseen
  domain.

## Follow-up: capacity buys familiarity

`mechanism_holdout_capacity.py` repeats the design at 15 and 120 leaves.
Totals over the six families, 1,728 tasks:

| leaves | in distribution | held out | in-dist minus E0 | held-out minus E0 | transfer gap |
| --- | --- | --- | --- | --- | --- |
| 15 | 1000 | 762 | -20 | -258 | +238 |
| 60 | 1194 | 716 | +174 | -304 | +478 |
| 120 | **1230** | **706** | +210 | -314 | **+524** |

Held-out minus E0 by family at 15, 60 and 120 leaves: transform -45, -62, -58;
ast -32, -40, -38; novel operator -43, -26, -17; stack -7, -24, -39; mutation
-11, -22, -32; self edit -120, -130, -130.

In-distribution performance rises monotonically with capacity, held-out
performance falls monotonically, and the transfer gap widens from +238 to +524.
Stack and mutation are within noise of E0 when held out at 15 leaves (intervals
-22 to +7 and -23 to +2) and regress clearly at 120. Self-edit is catastrophic
at every capacity. AST, held out, selects 9, 1 and 3 correct programs in 288.

So "a larger model is a better evaluator" is itself family-bound: the extra
capacity is spent on the familiar generators and makes the model worse on an
unfamiliar one. The gate stated above is sharpened accordingly. **Held-out
mechanism performance must be reported at the deployed capacity, and any
capacity increase must be justified on held-out mechanisms, not only in
distribution.** Source: `analysis/mechanism-holdout-verifier-leaves15-20260921.json`,
`analysis/mechanism-holdout-verifier-leaves120-20260921.json`.
