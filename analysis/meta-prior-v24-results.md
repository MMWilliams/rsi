# V24 retained synthesis prior: transfer null

Status: audited null result. This experiment directly tests whether V23’s interactive gain can be retained without final-bank oracle access.

## Protocol

Development tasks received up to two counterexample-guided oracle queries. The resulting programs supervised a pairwise structural ranker over visible-consistent candidates. The ranker was then frozen. Admission and final tasks were solved passively: no hidden examples were supplied to the ranker or synthesizer.

## Result

| Arm | Admission | Fresh final |
| --- | ---: | ---: |
| Baseline visible-candidate cost ranking | 20/24 | 23/24 |
| Learned pairwise prior | 20/24 | 23/24 |

The learned prior was admitted because it did not regress on admission, but it produced no final-bank gain. Twenty-two of 24 development tasks yielded a candidate that could be matched to the interactive oracle-resolved program; the fit made 36 pairwise updates.

## Audit and interpretation

The audit replayed 22 active training tasks and 96 passive admission/final evaluations, re-fit the prior, checked all rankings and hashes, and verified 23 sealed artifacts. Audit status: passed.

This is a meaningful negative result: oracle feedback can repair individual synthesis trajectories, but a small hand-featured ranker does not retain that repair as a general passive capability. The next intervention must transfer richer objects than ranking weights—likely grammar induction, learned counterexample generation, or self-modifying search code.

Artifact: `runs/meta-prior-v24-20260917/`.
