# V41 retrieval versus shape-macro ablation

Status: audited attribution result. V41 compares baseline, shape-only, retrieval-only, and combined arms after the same active verified training loop.

| Arm | Development | Admission | Fresh final |
| --- | ---: | ---: | ---: |
| Baseline | 20/24 | 12/24 | 16/24 |
| Shape macros only | 20/24 | 13/24 | 17/24 |
| Retrieval only | 22/24 | 12/24 | 16/24 |
| Combined | 22/24 | 13/24 | 17/24 |

The fresh-bank gain is reproduced by shape macros alone; retrieval-only ties baseline and combined does not exceed shape-only. This narrows the mechanism: the useful intervention is verified macro compression, while the current task-signature memory adds no independent capability.

The audit replayed 288 arm/split evaluations and checked 25 sealed artifacts. This remains bounded evidence, not proof of RSI.

Artifact: `runs/retrieval-ablation-v41-20260917/`.
