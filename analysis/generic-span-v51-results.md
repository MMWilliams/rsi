# V51 generic boundary-span induction

Status: audited two-seed schema-level transfer result. V51 removes the named `Before`/`After` operator vocabulary and exposes only a generic `Slice(boundary,boundary)` algebra. Boundary descriptors are inferred from visible delimiter occurrences and promoted after verified training success.

| Seed | Fixed-DSL baseline final | Generic span final | Verified training tasks |
| --- | ---: | ---: | ---: |
| 2026091902 | 11/24 | 24/24 | 45/48 |
| 2026091903 | 14/24 | 24/24 | 46/48 |

Across two fresh banks, generic boundary-span induction improved final performance from 25/48 to 48/48. Unlike V50, no named `Before` or `After` operator was supplied to the learner; the successful hypotheses were synthesized as boundary pairs such as start-to-delimiter and delimiter-to-end.

This is the strongest current capability-expansion result, but it still is not open-ended RSI. The boundary algebra, delimiter observation rule, task generator, and verifier remain researcher-authored. The next milestone is allowing the system to propose and validate new boundary primitives or task generators without a fixed boundary vocabulary.

Both runs passed independent audits, replaying 288 evaluation rows and checking 20 sealed artifacts per run.

Artifacts: `runs/generic-span-v51-20260918/` and `runs/generic-span-v51-20260919-seed03/`.
