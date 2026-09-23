# V14 replay-and-gate neural result

Run: `runs/neural-gated-v14-20260917`.

This run added a held-out validation gate and exact adapter rollback to the
verified LoRA loop. Each self-training proposal was scored on the same fresh
validation samples as its parent; updates were accepted only if both pass@1
and pass@16 were non-decreasing and at least one improved.

| Checkpoint | pass@1 | pass@8 | pass@16 |
| --- | ---: | ---: | ---: |
| Unadapted final | 0/16 | 0/16 | 0/16 |
| Round 1 final, rejected update | 0/16 | 1/16 | 1/16 |
| Round 2 final, rejected update | 0/16 | 2/16 | 3/16 |

Both proposed updates were rejected on validation: round 1 fell from
1/8 to 0/8 at pass@16, and round 2 stayed at 0/8 rather than improving.
The run's tensor-hash assertions verified exact rollback to the bootstrap
adapter. The independent archive audit passed: 36 journal events, 48 final
sample sets, 32 validation sample sets, and 19 verified rows were rechecked.

The positive result is therefore verified bootstrap distillation, not gated
self-training: the rolled-back adapter produced 3/16 final tasks at pass@16
under one generation seed. This supports retention of a small local learned
capability while showing that replay-and-gate did not create an additional
validated improvement in this trial. It remains far from evidence of RSI:
the system uses one small neural model, one seed, tiny banks, a fixed DSL,
finite hidden examples, and a same-host symbolic oracle.
