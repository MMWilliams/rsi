# Fresh-task search validation — 2026-09-16

## Decision and scope

The filter correction passed the preregistered fresh-task replication screen.
It improved both first-choice correctness and deterministic coverage@64 overall,
with joint gains in five of six seed groups. The sixth tied on first choice and
improved coverage. This supports a controlled verified-frontier training study.
The current default worker has not been promoted; RSI remains unproved.

Run: `runs/search-validation-20260916-v8/`. Protocol:
`EXPERIMENT-v8-search-validation.md`. Audit status: **passed**: 24 artifact
hashes, 9,796 journal events, 576 regenerated tasks, 4,608 reexecuted searches,
66,680 regraded frontier programs and 576 independently reconstructed mixtures.

The intervention is human-directed: allow program pieces that return an empty
string on some visible examples. Both arms use the same fixed search policy,
cheaper-route reopening, base settings and common library. No model trained,
no improver changed itself, and no mission-domain application was evaluated.

## Prospective design and accounting

Six new generator seeds (269, 281, 293, 307, 317, 331), 96 tasks each. Reference
templates were excluded from all prior archived protected banks and between the
new groups. Every task has three visible and thirteen hidden examples. The search
receives only ID and visible examples. Source, protocol and configuration were
archived before bank generation; all 4,608 searches and exact replays closed before
hidden grading began. No outcome-dependent tuning or stopping occurred.

Each filter was evaluated at ceilings 32, 64, 128 and 512. The fixed mixture
combines baseline@64 and corrected@64, deduplicates by program, ranks by cost,
text length and text, and retains at most 64. Both component costs are charged.
The mixture was specified before results; it is not an oracle-selected policy.

Coverage@k means at least one finite-example-verified program among the first k
deterministic search candidates. This differs from IID neural pass@k. Groups
are generator seed groups, not independent model training seeds. Prior exclusions
condition the distribution, so compare paired arms within this study.

## Primary result: ceiling 128

| Measure | Original filter | Corrected filter |
| --- | ---: | ---: |
| First-choice correct | 332/576 (57.64%) | 377/576 (65.45%) |
| Coverage@64 | 374/576 (64.93%) | 438/576 (76.04%) |
| Actual expansions | 38,143 | 57,724 |
| Primitive executions | 2,692,724 | 4,406,436 |
| Process CPU seconds | 8.69 | 14.28 |
| Wall seconds | 9.29 | 14.90 |

First choice: 62 paired wins, 17 losses, net **+7.81 percentage points**.
Coverage@64: 82 wins, 18 losses, net **+11.11 points**. Actual costs increased
despite equal ceilings. Times above cover the first search executions, excluding
replay, grading and archive work. Separate replay timing/counters are retained.

| Seed | Original first choice | Corrected first choice | Original coverage@64 | Corrected coverage@64 |
| --- | ---: | ---: | ---: | ---: |
| 269 | 55 | 61 | 64 | 75 |
| 281 | 60 | 69 | 65 | 75 |
| 293 | 56 | 68 | 63 | 75 |
| 307 | 58 | 58 | 65 | 69 |
| 317 | 49 | 59 | 55 | 70 |
| 331 | 54 | 62 | 62 | 74 |

## Budget curves and fixed mixture

| Filter / expansion ceiling | First correct | Coverage@64 | Actual expansions | CPU seconds | Wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original / 32 | 297 | 323 | 11,953 | 6.03 | 6.78 |
| Original / 64 | 323 | 362 | 21,467 | 7.19 | 7.70 |
| Original / 128 | 332 | 374 | 38,143 | 8.69 | 9.29 |
| Original / 512 | 350 | 397 | 118,068 | 18.17 | 18.47 |
| Corrected / 32 | 320 | 354 | 15,963 | 9.47 | 9.95 |
| Corrected / 64 | 358 | 414 | 30,548 | 11.00 | 11.80 |
| Corrected / 128 | 377 | 438 | 57,724 | 14.28 | 14.90 |
| Corrected / 512 | 410 | 479 | 206,097 | 37.73 | 38.60 |
| Fixed mixture / 64+64 | 380 | 439 | 52,015 | 18.19 | 19.50 |

At these measured points, corrected@128 outperforms original@512 on both quality
measures using less CPU time, wall time and fewer expansions. It still uses more
primitive evaluations. This is evidence of a favorable measured runtime tradeoff,
not a strict matched-total-compute experiment or a hardware-independent guarantee.
CPU and wall timings are host-specific; the full test suite briefly ran in a
separate process during the study's early stage. Process CPU excludes that other
process's CPU, but scheduling can affect wall time. Neither timing is an exact
replay invariant.

The mixture gains three first-choice tasks and one coverage@64 task relative to
corrected@128, while paying for 7,099,160 primitive executions and both pools.
Against original@128 it has 57 first-choice wins and nine losses. Relative to
corrected@128 it has 11 wins and eight losses. It reduces baseline regressions,
but the small net gain does not establish that it is the best allocation policy.

## Logging, audit and interpretation

The run completed in **297.03 seconds**, including 44.06 seconds of grading.
First executions plus exact replays consumed 999,926 expansions, 56,793,280
primitive charges and 5,508,320 generated nodes. Host grading recorded an upper
bound of 2,133,760 example evaluations across both interpreters. There were zero
model calls or training updates. The separate audit's reexecution is additional
verification work, not included in those experimental totals.

The full suite passed **61 tests**, with two known PEFT fixture warnings. New
checks reject hidden grades entering the fixed merger and detect an omitted
search after journal rehashing and archive resealing. Journals preserve every
request, result, frontier, replay digest, timing, grade and paired task outcome.
Code hashes, seed configuration and prior exclusion hashes identify provenance.

The independent audit regenerates banks, reexecutes searches, reconstructs the
mixture with a separate implementation, regrades via the published interpreter,
and recomputes metrics and the declared screen. Shared generator/search code,
finite-example correctness, unauthenticated host hashes and unrepeatable timing
remain limits. Exact replay establishes reproduction, not improvement.

## Why individual outcomes changed

Post-audit analysis in `analysis/search-validation-20260916-v8-changes.json`
records the old/new programs, visible inputs, costs and mechanism evidence for
all 79 changed first choices. All 62 gains selected a program not expressible
by any concatenation of entries in the old filtered pool. This checks exact
program syntax, including multi-atom macros; it does not establish that every
alternative correct program was unreachable.

All 62 gains occurred on tasks where the original search returned no visible
solution. Of the 17 regressions, the corrected search returned no visible
solution in 16 cases. This suggests a visible-only fallback policy as a future
control: preserve a found original solution and spend additional search only
when it fails. That policy was not an arm in the preregistered study; these
inspected outcomes cannot establish its prospective performance or cost benefit.

For 13 of the 17 regressions, the old correct program was absent from the
corrected frontier at 128 but present at 512. The remaining four were absent
from both recorded corrected frontiers. A frontier is capped, so absence does
not prove that no suitable program was generated internally. These observations
support a representational benefit and a bounded-search tradeoff, rather than
claiming all regressions arise from final candidate ranking.

This descriptive analysis consulted saved grades after the study, selected no
new policy and issued no new hidden queries. It charged 948,672 extra primitive
evaluations to reconstruct visible pools, separately from study and audit costs.
Its code hash and source result/audit hashes are recorded. The representation
helper was checked for multi-atom macros, order and empty results.

## Next step toward RSI

Use the corrected amplifier in an explicitly versioned experimental arm and test
task-balanced verified-frontier distillation with retained-data controls. Generate
new training and evaluation banks; this inspected validation bank is not a fresh
holdout for the next adaptive policy. Keep original-filter controls and report
all acquisition, replay, training and evaluation costs.

Neural retention and large-k coverage must improve before reconnecting to the
full interleaved loop. Common-ancestor improver tests, inheritance ablations,
self-created edit vocabulary and application-specific evaluations remain open.
Latest related-work check: `research-search-validation-2026-09-16.md`.
