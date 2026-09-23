# V28 active epsilon-transition retention

Status: audited null result. V23 showed that hidden counterexamples can expose transitions that emit nothing on the initial visible examples. V28 ran active two-query CEGIS on development tasks, mined any fragments empty on every visible example but useful on hidden examples, froze the resulting grammar extensions, and evaluated later tasks passively.

| Arm | Development | Admission | Fresh final |
| --- | ---: | ---: | ---: |
| Bayesian passive control | 21/24 | 17/24 | 18/24 |
| Retained epsilon library | 21/24 | 17/24 | 18/24 |

The development bank produced zero eligible epsilon macros. The independent audit replayed all 24 active training trajectories and 144 passive evaluations, and checked 23 sealed artifacts.

Interpretation: interactive CEGIS can be highly effective when oracle access remains available, but its hidden transitions are not automatically reusable across tasks. Retention requires a richer abstraction or a bank where such transitions recur. Oracle feedback was used during development, so this is not passive RSI evidence.

Artifact: `runs/epsilon-retention-v28-20260917/`.
