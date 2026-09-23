# V62 arithmetic-family discovery

Status: audited two-seed result. V62 makes several operator families compete on a hidden-symbol bit-transition domain: runtime predicates, character-set memorization, divisor-derived modular predicates, and bitwise predicates synthesized from visible ordinal observations.

| Representation | Seed 24 final | Seed 25 final |
| --- | ---: | ---: |
| Baseline | 0/24 | 0/24 |
| Reflective predicates | 0/24 | 0/24 |
| Memorized `char_set` | 0/24 | 0/24 |
| Divisor-derived modulus | 0/24 | 0/24 |
| Synthesized bitwise predicate | 24/24 | 24/24 |

The bitwise arm reached 24/24 development, admission, and final on both seeds and was selected twice. This shows that a new arithmetic operator family can be the decisive capability substrate when earlier abstractions fail, and that hidden-symbol generalization is not limited to modular arithmetic.

The remaining limitation is important: the competing arithmetic families were still authored by the researcher. The next experiment should generate the operator family itself from failed hypotheses or a general expression grammar, rather than present `mod` and bitwise families as named arms.

Both independent audits passed, replaying 360 evaluation rows and checking 22 sealed artifacts per run.

Artifacts: `runs/bitwise-v62-20260918/` and `runs/bitwise-v62-20260919-seed25/`.
