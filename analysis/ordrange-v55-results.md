# V55 raw ordinal-range predicate transfer

Status: audited two-seed result. V55 removes Unicode categories from the observation language. It identifies output prefix/suffix cut glyphs in delimiter training, induces raw code-point intervals between those cuts, freezes the resulting ordinal-range predicates, and transfers the generic span schema to the delimiter-free letter/digit-transition domain. The invention arm is restricted to induced semantic programs.

| Seed | Baseline development | Ordinal induced development | Baseline admission | Ordinal induced admission | Baseline final | Ordinal induced final |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026091910 | 18/24 | 24/24 | 21/24 | 24/24 | 23/24 | 24/24 |
| 2026091911 | 23/24 | 20/24 | 18/24 | 21/24 | 20/24 | 23/24 |

Using the fixed `ord_c10` arm, pooled final performance was 47/48 versus 43/48 baseline. The induced vocabulary contained five raw intervals; the useful transferred intervals included code-point ranges corresponding to the observed digit and letter regions, but the system was not given those semantic labels. Both runs verified all 48 delimiter-training tasks and selected only span programs in the invention arm.

V55 is a weaker but more revealing result than V54: it trades some accuracy for a lower-level observation language. It still has important limits: ordinal ranges are themselves a fixed representational bias, the domains are synthetic, and the character alphabets overlap between training and evaluation. The next pressure test should use disjoint alphabets and evolve the predicate grammar itself rather than fixing interval syntax.

Both independent audits passed, replaying 288 evaluation rows and checking 21 sealed artifacts per run.

Artifacts: `runs/ordrange-v55-20260918/` and `runs/ordrange-v55-20260919-seed11/`.
