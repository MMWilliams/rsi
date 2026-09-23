# V64 compositional expression synthesis

Status: audited two-seed result. V64 replaced V63's separate modulus/bitwise predicate invention with one typed ordinal-expression grammar. The grammar contains ordinal access, arithmetic transforms, comparisons, boolean composition, and a signature-indexed search procedure. The evaluation bank mixed modulus, bit, threshold, and compound-OR hidden mechanisms without exposing their family labels.

| Representation | Seed 34 final | Seed 35 final |
| --- | ---: | ---: |
| Baseline | 0/24 | 0/24 |
| Reflective predicates | 0/24 | 0/24 |
| Memorized `char_set` | 3/24 | 7/24 |
| Previous universal ordinal grammar | 17/24 | 20/24 |
| Generic compositional grammar | 24/24 | 24/24 |

The generic grammar reached 24/24 development, admission, and held-out final on both seeds and was selected twice. It synthesized compound boolean expressions for the new OR-of-arithmetic mechanism; the previous grammar could express only one modular or bit predicate and fell behind on the same banks.

Both independent audits passed. Each replayed 360 evaluation rows and checked 23 sealed artifacts, for 720 rows and 46 artifacts across the two replications. The audited archives are `runs/expression-v64-20260924/` and `runs/expression-v64-20260925/`.

## Interpretation

This supports a stronger bounded claim than V63: a system can search a shared typed program language, compose primitive arithmetic predicates, and create an executable compound operator that was not supplied as a named controller arm. Signature indexing reduced the synthesis search from naive quadratic enumeration to behavior-compatible combinations, making the approach computationally viable.

It still does not establish open-ended RSI. The primitive vocabulary (`ord`, modulus, bit, comparisons, boolean operators), span schema, visible target alignment, hidden-task generator, and complexity limits remain researcher-authored. The system is composing within an engineered substrate rather than inventing and validating arbitrary new substrates or improving its own learning process.

## Next discriminating test

Let the system propose and test new primitive functions from failure traces—e.g. affine maps, bit slices, finite differences, and recursively defined transforms—under a costed typed grammar. The proposal mechanism itself should be selected on held-out mechanism families, with no named operator family exposed in the runner.

An earlier unsealed pilot (`expression-v64-20260920` and `expression-v64-20260920b`) was excluded from the claim: it either used the pre-interleaving generator or was terminated during naive quadratic composition. It remains a debugging record, not research evidence.
