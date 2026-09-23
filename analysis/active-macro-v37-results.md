# V37 active-trajectory macro induction

Status: audited exploratory signal. V37 runs active CEGIS on development tasks, independently verifies the returned programs, mines recurring multi-atom shapes from those self-generated trajectories, and then uses the resulting macros as width-one transitions in a passive search on admission and fresh banks.

| Run | Control final | Learned final | Control admission | Learned admission |
| --- | ---: | ---: | ---: | ---: |
| V37-A | 12/24 | 13/24 | 15/24 | 16/24 |
| V37-B | 13/24 | 13/24 | 18/24 | 19/24 |
| Pooled | 25/48 | 26/48 | 33/48 | 35/48 |

All 48 development tasks produced verified active trajectories. The learned arm improved one fresh bank and tied the other, yielding a small pooled gain. This is more RSI-relevant than reference-mined libraries because the abstraction corpus was produced by the system’s own verified loop, but it still depends on oracle feedback during training and uses a fixed DSL, macro schema, and researcher-bounded width constraint.

Both archives passed independent replay, covering 288 passive evaluation rows and 48 verified training programs. This is bounded evidence of self-generated substrate improvement, not proof of open-ended RSI.

Artifacts: `runs/active-macro-v37-20260917/` and `runs/active-macro-v37b-20260917/`.
