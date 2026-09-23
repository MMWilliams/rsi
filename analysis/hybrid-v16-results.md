# V16 neural-symbolic hybrid result

This experiment tested a different route to RSI: the adapted model proposes
DSL programs, symbolic search ranks and verifies them, verified hybrid
trajectories are distilled back into the adapter, and the post-update system
is evaluated on a fresh final bank. Two bank/seed replications were audited.

| Run | Symbolic baseline | Raw neural pre → post pass@16 | Hybrid pre → post pass@16 | Ranked hybrid |
| --- | ---: | ---: | ---: | ---: |
| `hybrid-v16-20260917` | 10/16 | 2/16 → 2/16 | 10/16 → 10/16 | 10/16 |
| `hybrid-v16b-20260917` | 7/16 | 3/16 → 4/16 | 7/16 → 7/16 | 7/16 |

The hybrid verifier converted weak raw neural proposals into valid symbolic
programs, raising raw pass@16 to the symbolic baseline in both replications.
In the second seed, verified retraining improved raw pass@8/pass@16 from
18.75% to 25%, but hybrid task coverage did not move. Thus the bottleneck is
not only model generation: the fixed symbolic search/ranking kernel limits
which newly proposed programs can become useful capability.

The archives passed independent audits: 25 journal events per run, 560
selected programs replayed and regraded per run, and 15/18 verified hybrid
rows rechecked. This is evidence for a neural-symbolic amplifier and a
clearer failure mode, not evidence of recursive self-improvement: the DSL,
search kernel, model seed, task banks, and host oracle remain bounded.
