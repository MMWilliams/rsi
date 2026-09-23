# V40 episodic retrieval plus macro substrate

Status: audited combined-arm signal, attribution constrained by V41 ablation. V40 added task-conditioned retrieval of verified development programs to the active-trajectory macro-compression substrate.

| Run | Control final | Combined final | Control admission | Combined admission |
| --- | ---: | ---: | ---: | ---: |
| V40-A | 16/24 | 18/24 | 10/24 | 11/24 |
| V40-B | 13/24 | 16/24 | 14/24 | 14/24 |
| V40-C | 17/24 | 18/24 | 19/24 | 22/24 |
| Pooled | 46/72 | 52/72 | 43/72 | 47/72 |

The combined arm produced a sizeable pooled signal. However, V41 isolated the components: retrieval-only tied baseline while shape-only matched the combined arm. Therefore V40 supports the macro substrate line, but does not establish that episodic retrieval independently adds capability.

All three V40 archives passed independent replay, covering 432 evaluations and 75 sealed artifacts. Oracle-dependent training, a researcher-authored task signature, fixed DSL/macro schema, and small banks remain limitations.

Artifacts: `runs/retrieval-macro-v40-20260917/`, `runs/retrieval-macro-v40b-20260917/`, and `runs/retrieval-macro-v40c-20260917/`.
