# V31 tabular RL query controller

Status: audited negative result. V31 applies tabular Q-learning to active CEGIS query allocation. The controller observes only the current query count and a coarse candidate-count state, then chooses `stop` or `query`; the policy is trained on development tasks with a small query-cost penalty.

| Split | Fixed q=0 | Fixed q=2 | Learned RL | RL mean queries |
| --- | ---: | ---: | ---: | ---: |
| Development | 19/24 | 24/24 | 22/24 | 0.38 |
| Admission | 17/24 | 24/24 | 20/24 | 0.50 |
| Fresh final | 20/24 | 24/24 | 22/24 | 0.50 |

The gate selected fixed q=2. The RL policy was eligible because it did not fall below the q=0 admission baseline, but it lost four fresh tasks relative to fixed q=2 and used more queries per task than the fixed controller on this bank (0.50 versus 0.21). This falsifies the narrow hypothesis that a shallow tabular policy can learn a reliable stop/query decision from these observables.

The archive passed independent replay: 216 evaluation rows were re-evaluated and the selection gate matched. Limitations include oracle-dependent training/evaluation, a fixed DSL, coarse tabular state features, and small banks. This is not proof of RSI.

Artifact: `runs/rl-query-v31c-20260917/`.
