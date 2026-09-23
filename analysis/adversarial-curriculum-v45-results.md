# V45 adversarial curriculum selection

Status: audited attribution result. V45 generated a 72-task training pool, measured visible-only baseline difficulty, verified trajectories with CEGIS, and compared uniform versus hard-case trajectory selection for macro learning.

| Seed | Baseline | Uniform-17 | Uniform-24 | Hard-low-24 | Hard-empty |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2026091892 | 10/24 | 12/24 | 11/24 | 13/24 | 13/24 |
| 2026091893 | 14/24 | 16/24 | 17/24 | 15/24 | 15/24 |

Pooled fresh performance was 24/48 for baseline, 28/48 for Uniform-17, 28/48 for Uniform-24, and 28/48 for each hard-case curriculum. Verified macro learning transfers, but visible-only adversarial selection did not outperform size-matched uniform selection.

Both runs passed independent audits, replaying 432 evaluation rows and checking 26 sealed artifacts per run. The curriculum uses oracle feedback during training, a fixed DSL/macro schema, and small synthetic banks.

Artifacts: `runs/adversarial-curriculum-v45-20260917/` and `runs/adversarial-curriculum-v45-20260918-seed93/`.
