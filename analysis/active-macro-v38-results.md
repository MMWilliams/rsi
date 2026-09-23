# V38 deeper active-trajectory macro compression

Status: audited exploratory signal. V38 repeats the V37 active-trajectory loop while allowing learned shape macros up to four atoms long, still counted as one transition inside a width-two passive search.

| Run | Macro horizon | Control final | Learned final | Control admission | Learned admission |
| --- | ---: | ---: | ---: | ---: | ---: |
| V37-A | 3 | 12/24 | 13/24 | 15/24 | 16/24 |
| V37-B | 3 | 13/24 | 13/24 | 18/24 | 19/24 |
| V38 | 4 | 17/24 | 18/24 | 17/24 | 17/24 |
| Pooled | — | 42/72 | 44/72 | 50/72 | 52/72 |

The deeper active-generated macro library produced a fresh-bank gain while preserving admission performance. Across the three archives, learned compression improved two banks and tied one. This is the clearest current evidence that a verified loop can create reusable substrate transitions, although the effect remains bounded and modest.

All three archives passed independent replay, covering 432 passive rows and 72 verified training programs. Oracle access during development, a fixed DSL/macro schema, and a researcher-bounded width constraint remain; this is not proof of open-ended RSI.

Artifacts: `runs/active-macro-v37-20260917/`, `runs/active-macro-v37b-20260917/`, and `runs/active-macro-v38-20260917/`.
