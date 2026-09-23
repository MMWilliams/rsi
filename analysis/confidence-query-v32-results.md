# V32 structural Bayesian confidence query gate

Status: audited unstable signal. V32 trained a Naive-Bayes-style structural confidence model from development CEGIS trajectories, omitted literal constant values, and queried the oracle when confidence fell below one of four preregistered thresholds.

| Run | Arm | Admission | Fresh final | Mean final queries |
| --- | --- | ---: | ---: | ---: |
| V32-A | Fixed q=2 | 24/24 | 24/24 | 0.12 |
| V32-A | Confidence 0.90 | 22/24 | 23/24 | 0.29 |
| V32-B | Fixed q=2 | 24/24 | 22/24 | 0.33 |
| V32-B | Confidence 0.90 | 20/24 | 18/24 | 0.17 |

The first fresh bank suggested a one-task accuracy tradeoff, but the second bank showed a four-task deficit. The gate selected fixed q=2 in both archives. Thus structural confidence can modulate oracle use, but this small Bayesian model does not provide stable transferable capability.

Both archives passed independent replay, covering 360 rows each. Limitations include the fixed DSL, oracle-labeled development trajectories, Naive Bayes independence, and small banks. This is not proof of RSI.

Artifacts: `runs/confidence-query-v32-20260917/` and `runs/confidence-query-v32b-20260917/`.
