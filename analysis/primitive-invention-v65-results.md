# V65 failure-driven primitive invention

Status: audited two-seed result. V65 extended the typed expression substrate with transform atoms proposed from the failure boundary: floor division followed by modulus, shifted/XOR (Gray-code) bits, and masked multi-bit fields. The same semantic span solver then searched these proposals without receiving a hidden rule label.

| Representation | Seed 37 final | Seed 38 final |
| --- | ---: | ---: |
| Baseline | 0/24 | 0/24 |
| Reflective predicates | 0/24 | 0/24 |
| Memorized `char_set` | 0/24 | 0/24 |
| Previous universal ordinal grammar | 0/24 | 0/24 |
| V64 expression grammar | 6/24 | 5/24 |
| Failure-driven primitive invention | 20/24 | 20/24 |

Primitive invention was selected on both seeds. It solved all quotient-periodic and Gray-code tasks in the first replication and most multi-bit-field tasks; the remaining errors are retained in the archives rather than being screened out.

Both independent audits passed. Each replayed 432 evaluation rows and checked 24 sealed artifacts, for 864 rows and 48 artifacts across the two replications. The audited archives are `runs/primitive-v65-20260927/` and `runs/primitive-v65-20260928/`.

## Interpretation

This is evidence that a bounded system can expand its executable hypothesis language with new numeric transforms and gain transfer on a mechanism family that the prior grammar cannot express reliably. The gain is not merely a re-ranking effect: the previous grammar had no direct floor-division, Gray-code, or multi-bit-field atoms.

The result still falls short of open-ended RSI. The transform catalog, constants, failure categories, coherence prior, visible target alignment, task generator, and complexity bounds were authored in advance. The system invents instances of a researcher-designed meta-language; it does not yet originate arbitrary primitives or improve its own proposal mechanism.

## Next discriminating test

Close the remaining hand-authored gap by learning transform proposals from failed visible truth signatures. Use a typed neural/grammar-guided proposer to emit candidate primitive ASTs, admit only proposals that improve held-out mechanism families, and test whether the proposer itself improves over generations without a fixed transform catalog.

The interrupted full-bank pilot `runs/primitive-v65-20260926/` is excluded from the claim because it was stopped before producing results; it records the initial quadratic-search cost failure.
