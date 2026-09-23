# V30 shape-prior beta sweep

Status: audited null result. V30 tests whether a bounded meta-selection over the hierarchical shape-prior strength can turn the V29 structural signal into a robust gain. The beta grid (`0, 1, 2, 3`) was fixed before evaluation; selection required no admission regression and used development performance as the tie-break.

| Arm | Beta | Development | Admission | Fresh final | Selection |
| --- | ---: | ---: | ---: | ---: | --- |
| Control | — | 18/24 | 17/24 | 18/24 | reference |
| Learned | 0 | 19/24 | 17/24 | 18/24 | eligible |
| Learned | 1 | 20/24 | 17/24 | 18/24 | selected |
| Learned | 2 | 20/24 | 17/24 | 18/24 | eligible |
| Learned | 3 | 20/24 | 17/24 | 18/24 | eligible |

All learned arms passed the admission gate and improved development scores over control, but all tied control on fresh final performance. The pre-registered selector therefore chose beta 1.0 by the development tie-break without claiming a final-bank gain. This is a useful negative result: bounded hyperparameter selection did not convert the V29 shape prior into additional held-out capability.

The archive passed independent replay: 360 evaluation rows were re-evaluated, all 22 sealed artifacts were checked, and the results hash matched. Limitations include the fixed DSL, researcher-authored beta grid, development references used for shape learning, and small fresh banks. This is not proof of RSI.

Artifact: `runs/shape-beta-sweep-v30-20260917/`.
