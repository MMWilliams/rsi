# V27 anti-unified library induction

Status: audited exploratory result with one isolated gain but no replication. This experiment mined recurring fragment shapes—such as substring/constant structure while abstracting concrete positions—and instantiated them from each task's visible-compatible atoms. The learned proposals were combined with the Bayesian prior and frozen before admission/final evaluation.

## Results

| Run | Training tasks | Arm | Admission | Fresh final |
| --- | ---: | --- | ---: | ---: |
| V27-A | 24 | Bayesian control | 17/24 | 22/24 |
| V27-A | 24 | Anti-unified library | 17/24 | 23/24 |
| V27-B | 24 | Bayesian control | 18/24 | 12/24 |
| V27-B | 24 | Anti-unified library | 18/24 | 12/24 |
| V27-C | 96 | Bayesian control | 16/24 | 22/24 |
| V27-C | 96 | Anti-unified library | 17/24 | 22/24 |

V27-A's +1 final task did not replicate in V27-B, and the larger 96-task training run improved admission by one task but tied on final. Across the two equal-size replications, the learned arm scored 35/48 versus 34/48 for control; this is an observed aggregate difference, not a confirmed per-bank gain.

All three archives passed independent replay: 144, 144, and 288 evaluation rows respectively, with 21 sealed artifacts checked per archive. Limitations include labeled development references, a fixed DSL, bounded template instantiation, and small fresh final banks. This is not evidence of RSI.

Artifacts: `runs/antiunification-v27-20260917/`, `runs/antiunification-v27b-20260917/`, and `runs/antiunification-v27c-20260917/`.
