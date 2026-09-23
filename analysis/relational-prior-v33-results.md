# V33 relational anti-unification prior

Status: audited null result. V33 extends anti-unification by preserving relative offsets between character positions within a multi-atom fragment, then adds the learned relational support to the generator likelihood.

| Arm | Development | Admission | Fresh final |
| --- | ---: | ---: | ---: |
| Generator control | 19/24 | 21/24 | 15/24 |
| Relational prior | 19/24 | 21/24 | 15/24 |

The learned library contained two recurring schemas. The gate accepted the learned arm because development and admission tied, but the fresh-bank result also tied. This indicates that preserving within-program position relations is not sufficient to transfer useful hypotheses in the current DSL.

The archive passed independent replay: 144 rows and 22 sealed artifacts were checked. Limitations include development-reference abstraction, a fixed DSL, a researcher-authored relation representation, and small banks. This is not proof of RSI.

Artifact: `runs/relational-prior-v33b-20260917/`.
