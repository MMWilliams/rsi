# Task-level top-200 evaluator feedback

**Result:** Task-level ranking beat candidate-level correctness training in two fresh tests at the same source-label and target-candidate-score counts. The larger independent replication passed its predeclared **objective** gate. The predeclared **incremental-checkpoint** and **integration** gates failed. This supports a scoped evaluator-training principle, not an improved improver or a positive recursive feedback loop.

## Controlled comparison

The early task-listwise and candidate-BCE models had the same 75,024 exact top-200 candidate labels available from 384 audited source tasks. Later models added the same 37,586 labels from 192 more source tasks, for **112,610 acquired labels** each. They saw the same 191 public features, specialist predictions, target candidate pools, and top-200 scoring budget. The listwise loss optimizes selection of any correct program within each task; BCE predicts each candidate's correctness separately. Listwise gradients used the 306/576 later source tasks with both correct and incorrect candidates; tasks without a within-task ranking signal were excluded by that objective. Thus acquisition is matched, while the objectives intentionally use the labels differently. Scrambled-added-label and duplicate-early-history listwise controls used the same architecture. No target family or hidden example entered the choices. Protocols: [first transfer](EXPERIMENT-task-listwise-top200-transfer.md), [replication](EXPERIMENT-task-listwise-top200-replication.md).

| Zero-query evaluator | First fresh 24 banks, correct / 192 | Replication 48 banks, correct / 384 |
| --- | ---: | ---: |
| Fixed dual specialists, top 100 | 83 | 161 |
| Fixed dual specialists, top 200 | 88 | 168 |
| Fixed candidate mean, top 200 | 87 | 171 |
| Early listwise, top 200 | 92 | 179 |
| **Later listwise, top 200** | **96** | **185** |
| Scrambled added feedback, top 200 | 79 | 155 |
| Duplicate early history, top 200 | 92 | 175 |
| Later BCE, matched 112,610 labels, top 200 | 89 | 173 |
| Prior top-100-trained stack applied at 200 | 88 | 170 |
| Top-200 reachable | 108 | 215 |

In the replication, later listwise minus matched-label BCE was **+12/384**, 14 positive and three negative banks, paired 95% bank-bootstrap interval **+4 to +20**. It met the predeclared objective gate. In the earlier 24-bank transfer it was +7/192, interval +2 to +13, but only six positive banks, so that original gate failed. Keep both records intact. The objective advantage is more credible than a result selected from one panel because the same frozen weights repeated it on another 48 banks.

The later checkpoint's advantage over early was +4/192 in the first test and +6/384 in replication. The first test missed its five-task/eight-bank gate; the replication missed its eight-task and positive-lower-bound gate (interval 0 to +12). Added verified feedback therefore has **not** established reliable incremental evaluator growth under the declared criteria. Scrambling feedback degraded the model, and later beat duplicate history by +10/384 in replication, but those controls do not repair the early-checkpoint failure.

The later listwise model beat fixed dual top-200 by +17/384 in replication (interval +9 to +26) and the prior stack by +15 (interval +7 to +23). The integration gate required at least +16 against *both*; it failed by one against the prior stack. Inference charged 225,384 candidate scores for listwise versus 150,256 for dual top-200 and 76,236 for dual top-100. The source acquisition was 112,610 labels, and common public preparation included 1,507,216 candidate-output prediction cells. Scores do not equate CPU/GPU time; the [replication manifest](runs/task-listwise-top200-replication-20260918/manifest.json) records generation and decision wall time. The cost/performance operating point remains a separate decision.

## Audit and limits

The [first audit](runs/task-listwise-top200-transfer-20260918/audit.json) rebuilt 192 tasks and 96,970 candidate labels. The [replication audit](runs/task-listwise-top200-replication-20260918/audit.json) rebuilt 384 tasks, 1,507,216 public output cells, 676,152 candidate-model prediction cells, and 188,402 exact candidate labels. Both passed. The initial first-run preparation failed before a target directory existed because Windows generator workers imported PyTorch and exhausted memory. Moving that import after the worker pool and limiting BLAS threads allowed the same frozen protocol and seed range to run; no labels had been opened by the failed attempt.

The exact interpreter judges finite hidden examples, not universal program correctness. The task distribution is synthetic familiar/shifted AST. The listwise output is a ranking score, not a calibrated probability. The replication's top-200 pool contained a correct program on 215/384 tasks and listwise selected 185, leaving **30 reachable ranking misses**. A retrospective oracle choosing among the seven tested evaluator arms reached only 193, eight above listwise; routing among these fixed arms has limited headroom. Candidate ranking and generation, plus independent mechanisms, remain material gaps.

## Consequence for the seed improver

Record task-level ranking loss as a **supported evaluator edit principle** at matched source labels on this benchmark. Keep its later checkpoint as a high-cost research component, while retaining the audited dual-specialist top-100 route as the lower-cost operating seed. Do not claim a grown improver: no later improver parent has selected this edit, improved its own edit policy, or produced a stronger child improver from the same frozen base on a second untouched bank.

The next parent-to-child test needs a catalog with genuinely different effects: ranking objective, shortlist/search changes and external sensor allocation, on multiple mechanisms. Each proposed edit must carry predicted gain, verified gain, harm and resource cost. Compare a later inherited effect table with early, scrambled, duplicate and fixed edit schedules under matched acquisition and deployment budgets. Then apply each resulting *child improver* to a second frozen base and oracle bank. Simple routing among the current top-200 evaluator arms cannot demonstrate much more than eight additional choices on the replication bank.

Raw evidence: [development screen](analysis/task-listwise-top200-development-20260918.json), [first outcomes](runs/task-listwise-top200-transfer-20260918/results.json), [replication outcomes](runs/task-listwise-top200-replication-20260918/results.json), [trainer](task_listwise_top200_development.py), [transfer runner](task_listwise_top200_transfer.py), [replication runner](task_listwise_top200_replication.py).
