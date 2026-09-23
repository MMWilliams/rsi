# V42 recursive macro composition

Status: audited two-seed result. V42 tests whether a verified active generation can improve the search substrate recursively: Gen-0 trajectories induce library 1; library 1 generates verified Gen-1 programs; Gen-0 plus Gen-1 then induce library 2.

| Seed | Arm | Development | Admission | Fresh final |
| --- | --- | ---: | ---: | ---: |
| 2026091886 | Baseline | 10/24 | 18/24 | 16/24 |
| 2026091886 | Generation 1 | 12/24 | 18/24 | 17/24 |
| 2026091886 | Generation 2 | 12/24 | 18/24 | 17/24 |
| 2026091887 | Baseline | 17/24 | 14/24 | 14/24 |
| 2026091887 | Generation 1 | 16/24 | 16/24 | 15/24 |
| 2026091887 | Generation 2 | 16/24 | 16/24 | 15/24 |

Across two independently audited banks, Gen-1 improved fresh final performance by one task on each bank: baseline 30/48 versus Gen-1 32/48. Gen-2 never exceeded Gen-1, also ending at 32/48. Gen-1 improved pooled admission from 32/48 to 34/48.

The result supports a bounded claim: verified active experience can create a reusable compression substrate that transfers to fresh tasks. It does not support recursive self-improvement yet, because the second generation added no capability, the macro schema and DSL were fixed by the researcher, and Gen-0 used oracle feedback.

Audits passed for both runs, replaying 216 evaluation rows per run and checking 26 sealed artifacts per run.

Artifacts: `runs/recursive-macro-v42-20260917/` and `runs/recursive-macro-v42-20260918-seed87/`.
