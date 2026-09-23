# V26 DreamCoder-style exact library learning

Status: audited null result. This experiment mined repeated contiguous multi-atom fragments from labeled development programs, froze them as reusable macros, and combined them with the generator-derived Bayesian selector.

| Arm | Development | Admission | Fresh final |
| --- | ---: | ---: | ---: |
| Fixed Bayesian prior | 16/24 | 16/24 | 18/24 |
| Learned exact-fragment library + Bayesian prior | 16/24 | 16/24 | 18/24 |

The learned library contained one fragment repeated twice. It passed the admission gate but produced no final-bank gain. The archive replayed 288 staged evaluations and verified 21 sealed artifacts.

Interpretation: exact fragment reuse is too sparse under disjoint program-template banks. A reusable library needs abstraction over positions and constants, motivating V27 anti-unification.

Artifact: `runs/library-learning-v26-20260917/`.
