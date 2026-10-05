# C-earned: results, 2026-10-05

Protocol `EXPERIMENT-mechanism-earned-confirmation.md` (frozen in c7898b0),
seeds 991101/992101, analysis `analysis/mechanism-earned-confirmation-20261005.json`,
audit `analysis/audit-mechanism-earned-confirmation-20261005.json` (passed:
1.1M evaluation picks checked against rebuilt constraints, 643 earning picks,
108 lifetimes replayed by the reference, groupings relearned exactly).

**C-earned failed.** Growth and structure passed in both replications; safety
failed in both.

| gate | A (991101) | B (992101) |
| --- | --- | --- |
| growth, 1,600 vs 400 earned worlds, pooled | +3639 [2616, 4673] pass | +3275 [2407, 4137] pass |
| structure, earned vs permuted, pooled | +5513 [4254, 6780] pass | +5498 [4346, 6639] pass |
| safety, no cell below champion | fail: new_triple 512 -326 [-518, -141], new_family 512 -187 [-305, -87] | fail: new_triple 256 -350 [-518, -193], 512 -285 [-421, -160] |

Reported: earned beats the champion at 128 and 1024-4096 on trained and
untrained combinations in both replications (+173 to +822); recovers 26% and
24% of the handed reference's pooled gain (644101: 47%). `mid` (800 worlds)
minus `early`: +1896 in A, -1831 in B, so growth is not monotone in worlds
(rule 13). At 400 worlds no atom cleared the 50-world bar in any replication,
so `early` is the champion and the growth gate is equivalent to earned beating
the champion pooled.

The development argument for not gating every-cell improvement (the handed
reference also fails at 256-512) did not hold on these seeds: handed beats the
champion at 512 everywhere but new_family. The 256-512 losses are the earned
grouping's, not the family agent's.

## What this does and does not establish

Not established: a safe earned representation. A representation learned only
from the agent's own picks, charged in scans, is pooled-better than none and
than its permuted copy, audited in two replications; it also loses
significantly at mid budgets, where the posterior commits to a wrong group with
the hedge at half. Per the protocol no second run is predeclared on these arms.

Diagnosis for the next level: the earned grouping covers about half the atoms
(the rest are ungrouped by the evidence bar) and recovers a quarter of the
handed gain; the losses sit where the family posterior acts on few
observations under a half hedge. Candidate L2 targets, each needing its own
screen: confidence-weighted (soft) membership in place of the bar; a hedge
share set by the grouping's own held-out likelihood; or level 2 learning the
bar itself across environments (Phase 2's selector).
