# V13 neural micro-loop result

This experiment ran the actual learned loop on a fresh bank: symbolic verified
bootstrap, Qwen3-0.6B LoRA distillation, verified self-training, a second
distillation, and held-out final sampling. Final generations were stored and
independently regraded.

## Audited replication

Run: `runs/neural-micro-v13-20260917c`.

| Checkpoint | pass@1 | pass@8 | pass@16 |
| --- | ---: | ---: | ---: |
| After symbolic bootstrap | 0/16 | 0/16 | 2/16 |
| After verified self-training round 1 | 2/16 | 3/16 | 3/16 |
| After verified self-training round 2 | 1/16 | 2/16 | 3/16 |

The first learned update improved pass@1 by 12.5 percentage points and
pass@16 by 6.25 points. The second update retained pass@16 but lost some
pass@1 and pass@8 performance, showing that the improvement is not monotonic.
The archive audit passed: 34 journal events, 48 final sample sets regraded,
and 13 verified training rows rechecked.

## Independent small replication

Run `runs/neural-micro-v13-20260917b` showed the same direction at lower
absolute performance: pass@16 increased from 6.25% after bootstrap to 12.5%
after round 1, and pass@1 reached 6.25% after round 2. That earlier archive
did not retain raw generations and is therefore not used as the primary audited
claim.

This is evidence that verified distillation can improve the local model on a
small task family. It is not yet evidence of recursive self-improvement: the
loop uses a fixed DSL, a symbolic bootstrap, one neural seed, tiny banks and a
finite oracle.
