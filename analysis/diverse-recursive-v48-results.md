# V48 quality-diversity recursive macro learning

Status: audited but unstable recursive-compounding result. V48 retains multiple independently verified, structurally distinct Gen-1 programs per development task before mining the Gen-2 library.

| Run | Population size | Baseline final | Gen-1 final | Gen-2 final |
| --- | ---: | ---: | ---: | ---: |
| Seed 2026091896 | 4 | 13/24 | 15/24 | 16/24 |
| Seed 2026091897 | 4 | 13/24 | 13/24 | 12/24 |
| Seed 2026091898 | 8 | 11/24 | 12/24 | 11/24 |

The first bank demonstrates genuine Gen-2 compounding, but the two replications do not: pooled results are 37/72 baseline, 40/72 Gen-1, and 39/72 Gen-2. More population diversity did not fix the variance. The correct conclusion is that quality-diversity retention can expose a recursive gain in some banks, but it is not yet a stable self-improvement mechanism.

Each run passed independent replay, covering 216 evaluation rows and 27 sealed artifacts. Training uses oracle verification, the DSL and macro schema remain fixed, and the task banks are small.

Artifacts: `runs/diverse-recursive-v48-20260918/`, `runs/diverse-recursive-v48-20260919-seed97/`, and `runs/diverse-recursive-v48-pop8-20260918/`.
