# V54 induced structural predicate transfer

Status: audited two-seed result with an attribution-controlled invention arm. V54 freezes unnamed character-category families induced from the delimiter-training bank and transfers the generic `Slice(run(predicate), run(predicate))` schema to a delimiter-free letter/digit-transition domain. The invention arm is evaluated only with induced semantic programs; it cannot fall back to the existing `WORD` or `DIGITS` primitives.

| Seed | Fixed baseline development | Induced development | Fixed baseline admission | Induced admission | Fixed baseline final | Induced final |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026091908 | 22/24 | 24/24 | 23/24 | 24/24 | 20/24 | 24/24 |
| 2026091909 | 21/24 | 24/24 | 22/24 | 24/24 | 21/24 | 24/24 |

The fixed `induced_c10` arm reached 48/48 final tasks pooled versus 41/48 baseline. It selected an induced semantic program on all 48 final tasks. The learner inferred three unnamed category families from training characters and reused them across the domain shift; no `alpha`, `digit`, `letter`, or `transition` predicate was supplied to the invention arm.

An initial exact-signature pilot underperformed because it split uppercase and lowercase letters into separate classes. Generalizing the induced representation to category families repaired that failure. This ablation is retained as evidence that representation design, rather than search budget alone, controls transfer.

The result is stronger than V53's attribution because old named primitives were excluded from invention-arm selection. It still does not establish open-ended RSI: Unicode category families are a fixed representational bias, the domains are synthetic, and the character alphabets overlap across training and evaluation.

Both independent audits passed, replaying 288 evaluation rows and checking 20 sealed artifacts per run.

Artifacts: `runs/induced-signature-v54c-20260918/` and `runs/induced-signature-v54d-20260919-seed09/`.
