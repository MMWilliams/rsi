# Incremental feedback training: listwise evaluator transfer

## Decision

**Promote the 120-epoch listwise ranker as a supported evaluator component for this synthetic three-family fixed-pool test.** Its frozen fresh-bank result passed the predeclared gate: 130/192 correct top choices versus E192's 105/192, wins on all six banks, a positive bank-resampling interval, and more correct choices than every tested control. This is retained evaluator improvement. It does **not** establish a better improver, recursive growth, or general intelligence outside this task distribution.

## What changed

The edit changed the feedback objective from independent candidate correctness classification to task-level ranking. A 175→32→1 ReLU model learned to place at least one oracle-verified correct program above incorrect programs in each training pool. It used the same 192 source tasks and **31,500 verified candidate labels** as E192. The 40, 80, and 120 epoch checkpoints were frozen before six new bank seeds, 902228–902233, were generated. The 120-epoch choice followed two previously inspected development banks and is therefore not a fresh hyperparameter search result.

The common test had 192 tasks across stack transition, mutation transition, and self-edit transition. Each task provided one visible example, a fixed pool from two candidate sources capped at 128 candidates each, eight unused probe inputs, and 15 held-out scoring examples. No oracle output query was used to choose a candidate. Candidate reachability was 191/192.

| Evaluator | Correct / 192 |
| --- | ---: |
| E192 independent classifier | 105 |
| Context expert | 110 |
| 50/50 context blend | 117 |
| Pairwise combination | 115 |
| Listwise, 40 epochs | 108 |
| Listwise, 80 epochs | 126 |
| **Listwise, 120 epochs** | **130** |

Listwise 120 minus E192 by bank was **+4, +6, +2, +2, +5, +6**. Exact resampling of six banks with replacement gave a 95% interval of **+17 to +33 correct choices per 192 tasks**. At the task level, the listwise model won 51 E192 disagreements and lost 26. The 40→80 gain was 18 tasks in aggregate; 80→120 added four, with two bank declines and one tie. The checkpoint path is incremental but not monotone on each bank.

Against the strongest context blend, the listwise margin was +13 overall but only four of six banks improved; its six-bank resampling interval was **0 to +26**. The predeclared gate required higher aggregate accuracy than the strongest control, which passed. Superiority to the blend with a strictly positive bank-level interval is **not** established.

The gain was concentrated in self-edit transition: **49/60** versus E192 **24/60**. Stack transition was 40/66 versus 41/66, and mutation transition 41/66 versus 40/66. The context blend scored 44, 41, and 32 respectively. Thus the ranker addresses a large weakness in one mechanism; further mechanism shifts still need testing.

## Cost, validation, and limits

Source candidate generation and oracle labeling took 123.4 seconds in the archived source run. A same-machine rerun of 120 GPU epochs with source checkpoint scoring took **25.8 seconds**; a full E192 logistic fit took **1.57 seconds**. These are timing reruns, not historical training logs. All evaluator decisions on the 192 stored candidate pools, including the controls, took 27.9 seconds in a timing rerun; fresh preparation including candidate generation took 68.3 seconds. Timing is machine and cache dependent. The listwise edit buys 25 additional correct choices over E192 with no additional source labels and materially more optimization compute.

The reconstruction audit passed: all 192 banks/tasks and candidate pools were regenerated; all 576 listwise checkpoint choices and all final outcomes were independently recomputed. The prepare stage froze choices before the score stage read held-out labels. This is an auditable code boundary, not independent host access control. Correctness means matching the 15 held-out examples in this synthetic string/program distribution, not universal program equivalence.

Protocol: `EXPERIMENT-listwise-evaluator-transfer.md`. Runner and audit: `listwise_evaluator_transfer.py`, `audit_listwise_evaluator_transfer.py`. Frozen data: `runs/listwise-evaluator-transfer-20260917/` with `manifest.json`, `sealed_bank.json`, `candidate_pools.json`, `frozen_decisions.json`, `results.json`, and `audit.json`.

## Next intelligence-growth test

The next step is to put this evaluator in the improver's edit catalog and test whether protected feedback lets an improver **choose or revise evaluator edits** better than a fixed listwise-120 policy on a new final bank, charging the same label and candidate budget. Then compare early and later improver parents on identical base systems and a second untouched bank. Stronger ranking alone is not evidence that the improver became better at improving itself.

An immediate development-only check tried the simplest admission-feedback selector. For each of six episodes, it used five other inspected banks as a prior, scored the first 16 tasks as admission feedback, and chose listwise-120 or the context blend by family for the final 16. Four fixed admission weights, including zero, each reached **61/96**, versus **68/96** for always using listwise-120. These labels are inspected development evidence; no fresh promotion test was run for this selector. Data and code: `analysis/listwise-selector-development.json`, `listwise_selector_development.py`. The next edit needs to improve edit-effect prediction or create a materially stronger evaluator, rather than merely switch by a coarse family label.

A second inspected-bank pilot standardized the two candidate-score vectors and blended them. Global listwise weights 0.8 and 0.9 each reached 133/192 versus 130 for listwise alone, a three-task development gain. Selecting a separate weight by family using five banks and testing the sixth totaled 130/192, exactly tying listwise. The small, unstable gain was not promoted to a fresh transfer claim. Code and data: `listwise_blend_development.py`, `analysis/listwise-blend-development.json`.
