# V29 hierarchical Bayesian shape prior

Status: audited exploratory signal with one gated gain and one rejected gain. V29 combines the generator-derived program log-probability with a learned anti-unified-shape likelihood. A fixed shape bonus (`beta=3.0`) was declared before evaluation; learned shape proposals were generated only from visible-compatible atoms.

| Run | Arm | Development | Admission | Fresh final | Gate |
| --- | --- | ---: | ---: | ---: | --- |
| V29-A | Generator prior | 15/24 | 21/24 | 17/24 | control |
| V29-A | Hierarchical shape prior | 15/24 | 21/24 | 18/24 | accepted |
| V29-B | Generator prior | 22/24 | 20/24 | 15/24 | control |
| V29-B | Hierarchical shape prior | 22/24 | 19/24 | 16/24 | rejected |

The learned arm gained one raw final task on both fresh banks, but V29-B regressed admission and was correctly rejected by the pre-registered gate. Thus the selected-arm result is 18/24 versus 17/24 in V29-A, and 15/24 versus 15/24 in V29-B. Raw combined performance was 34/48 versus 32/48; gated combined performance was 33/48 versus 32/48.

Both archives passed independent replay, covering 288 evaluation rows and 22 sealed artifacts per archive. The result is promising but unstable: the shape bonus is hand-chosen, training uses labeled development references, the DSL is fixed, and final banks are small. It is not proof of RSI.

Artifacts: `runs/shape-prior-v29-20260917/` and `runs/shape-prior-v29b-20260917/`.
