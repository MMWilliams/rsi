# Learned fragment proposals did not improve the solver

## Decision

**V7 failed its declared advancement screen. Do not promote fragment-proposer
inheritance as a better improver.** The later search correction restored cheaper
routes but did not rescue the recorded source proposals. RSI remains unproved.

Two separate results are preserved: the frozen prospective library experiment,
and a subsequent source-only diagnostic of a concrete search limitation. The
diagnostic does not replace the original result or constitute a replication.

## What v7 tested

Six new sources, six transfer conditions, six generations, and 192 final tasks.
Source and transfer harvest/development/admission slices contain 16 tasks per
generation. Each task has three visible and thirteen hidden examples. The
original search kernel uses a 128-expansion ceiling and four-atom programs.
All optimization closed before final scoring. The written protocol and exact
implementation are archived in `runs/library-inheritance-20260916-v7/source/`.

Every target solver starts with identical search settings and the original
thirteen-entry library (one historical four-atom entry is ignored by search).
Only the **proposer's memory** changes across g0/g3/g6/scrambled arms. An inherited
fragment is a candidate for an edit, not preinstalled solver capability. The
proposer extracts two-/three-atom fragments from verified harvest solutions,
ranks them using public development examples and tests two separate additions.
Positive development gain and nonnegative admission gain are required to install
one. Numeric-pair and frozen-library controls use the same query schedule.

This isolates a learned proposer from a pre-improved artifact. The proposing
algorithm and edit type remain fixed; this does not test unrestricted invention
of new edit types or neural coverage compounding.

## Final results

The common ancestor solved **104/192 tasks (54.1667%)**. Every g0, g3, g6,
scrambled and frozen-library target ended at exactly that score. All source
generation-3/6 solvers also retained their original configuration/library.

| Source | g0 memory | g3 memory | g6 memory | Scrambled g6 | Numeric pair | Frozen library |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 181 | 104 | 104 | 104 | 104 | 104 | 104 |
| 193 | 104 | 104 | 104 | 104 | 104 | 104 |
| 211 | 104 | 104 | 104 | 104 | 104 | 104 |
| 223 | 104 | 104 | 104 | 104 | 103 | 104 |
| 239 | 104 | 104 | 104 | 104 | 110 | 104 |
| 251 | 104 | 104 | 104 | 104 | 111 | 104 |
| Mean accuracy | 54.1667% | 54.1667% | 54.1667% | 54.1667% | 55.2083% | 54.1667% |

Counts are correct tasks out of 192 after six transfer generations. The g6-memory
contrasts are zero against g0, g3, scrambled and frozen, and **−1.0417 percentage
points** against the numerical control. No source beats both g0 and scrambled;
the screen required four of six plus all five positive mean contrasts.

The numerical pair accepted nine changes across six trajectories. Its small
positive mean is heterogeneous and does not demonstrate recursive improvement.
Its lower score for source 223 also shows that finite admission tests can miss
final regressions. Source/control tasks are shared within this experiment;
the six source results are not independent replications of the final task bank.

## What the change records explain

Source memories grew from zero to 47, 52, 50, 65, 61 and 55 unique fragments.
That increased proposal availability but never produced a beneficial measured
library change:

| Group | Actual fragment additions tested | No-op proposals | Installed fragments |
| --- | ---: | ---: | ---: |
| Sources | 44 | 28 | 0 |
| Transfer g0 | 47 | 25 | 0 |
| Transfer g3 | 63 | 9 | 0 |
| Transfer g6 | 71 | 1 | 0 |
| Transfer scrambled g6 | 68 | 4 | 0 |

Across **293 actual additions / 4,688 task–candidate evaluations**, only six
selected programs changed and no task's verified correctness changed. Search
trace hashes changed in 250 of these evaluations, so some internal search
behavior changed without useful output effects. These repeated observations
are not independent samples. The numerical control's attempts are separate.

The observed failure is therefore before admission: these selected fragments
did not improve development correctness. It is not a case of useful fragment
gains being systematically rejected by the gate. This does not establish that
every remembered fragment or every library-learning method lacks useful effects.

Scrambling preserved the primitive atom multiset within length buckets but
collisions reduced unique counts by one or two per source. One composition
remained unchanged in source 223. The complete control construction is logged;
the scrambled arm is not asserted to be perfectly matched in unique count.

Readable examples:

- `analysis/v7-rejected-fragment-explanation.md`: source 193, generation 6;
  provenance, rankings, both zero-gain proposals and the admission decision.
- `analysis/v7-accepted-numeric-explanation.md`: source 181's first numerical
  transfer change, including parameter difference, task wins/losses and costs.
- `analysis/library-inheritance-20260916-v7-diagnostics.json`: all group counts,
  source memory sizes, per-trajectory decisions and cost summaries.

## Search limitation found afterward, and its measured effect

The original kernel marks a syntactic state seen when first generated. A later,
cheaper macro route to that state can be discarded. Instrumenting all 704 source
task evaluations for the 44 actual fragment proposals found **four** such cases
while reproducing every original output exactly. One route to `Concat(' ', '/')`
was first recorded at cost 2.55; a later route costing 1.9125 was skipped.

The initial 128-task instrumentation pass found none; it included many no-op
proposals. Both that output and its original script are retained. Its legacy
`search_source_sha256` field hashes the source path string; the correctly named
`search_file_sha256` field supplies the content hash. The subsequent all-addition
analysis uses only the latter. No final task entered this diagnosis.

`rsi/search_reopen.py` now provides a separate corrected kernel: it tracks best
state cost, reopens cheaper paths, resets outgoing-edge progress and ignores
stale queued paths. A regression fixture reproduces the failure and verifies the
lower cost. This fixes a specific search invariant, not global optimality or
generalization. The default worker still uses the original kernel; future trials
must choose the corrected version explicitly rather than silently changing the
meaning of historical protocols.

The source-only counterfactual is frozen in
`runs/reopening-diagnostic-20260916-v7/`. It evaluated all original source
fragment requests **and their parents** with the corrected kernel: 70 unique
requests, **1,120 outputs plus 1,120 exact replays**, 25.87 seconds. Both the
published interpreter and host oracle graded the archived source examples.
The correction reopened four states and changed one selected program, but
changed no verified correctness. All 44 candidate-minus-parent gains stayed
zero. Its independent saved-output audit passed.

Thus this real limitation does **not explain the zero gains of these recorded
source proposals**. No new transfer trajectory or final-bank trial of the
corrected kernel has been run. It is not promoted as a better RSI mechanism.

## Cost and verification

V7 completed in **903.02 seconds**; measured worker/replay time was 879.55 seconds.
The ledger records 5,514,684 search expansions, 379,422,088 primitive execution
charges, 648,192 oracle example charges, and 466,227 visible-ranking primitive
upper-bound charges. Search/primitive charges include replay; oracle counts are
example-count upper bounds because execution can short-circuit. No neural
inference, weight training or paid model calls were used; zero incidents logged.

Every arm is charged the same corresponding source acquisition workload, even
when it discards the memory. Source work actually ran once and was shared.
Query counts and ceilings are matched; actual operations and timings differ.
The historical common-library acquisition remains shared prior work from v2.

| Condition | Source + transfer search expansions | Primitive charges | Ranking charges |
| --- | ---: | ---: | ---: |
| g0 | 926,324 | 64,880,180 | 84,005 |
| g3 | 926,316 | 64,882,004 | 116,422 |
| g6 | 926,316 | 64,882,668 | 153,523 |
| Scrambled g6 | 926,366 | 64,882,528 | 150,475 |
| Numeric pair | 926,254 | 64,874,764 | 84,127 |
| Frozen library | 926,300 | 64,874,764 | 84,005 |

Rows sum six source/transfer pairs and each includes the full shared source
charge. They exclude final scoring and historical library acquisition; summing
rows would count the shared source work repeatedly. These are not FLOP estimates.

The v7 independent audit passed **40,512 outputs, 1,597 evaluations, 504 edit
attempts, 42 trajectories, 2,404 journal events and 35 sealed artifacts**. It
reconstructed source certificates, scrambled controls, visible rankings,
proposal/admission arithmetic, common ancestors, cost totals and final ordering.
It regrades recorded programs rather than repeating all original searches;
hashes do not authenticate a hostile host. Certificates establish correctness on
the finite task examples, not equivalence on every possible input.

Verification: 50 tests passed before v7; **53 passed** after adding the corrected
kernel's regression/replay tests. Two known PEFT fixture warnings remain.

```powershell
.\.venv\Scripts\python.exe audit_library.py runs/library-inheritance-20260916-v7
.\.venv\Scripts\python.exe audit_reopening.py runs/reopening-diagnostic-20260916-v7
```

## Next decision

Measure whether any **unselected** visible-compatible source fragments offer
improvement at the same 128-expansion budget under the corrected kernel. Keep
this a source-only opportunity audit. It can distinguish a weak ranking rule
from a corpus with no useful available additions before spending another full
inheritance trial. If useful opportunities exist, test a new proposer on fresh
banks; otherwise change the abstraction or edit space. Do not retune against
the v7 final bank or lower the RSI success criterion.

No research, defensive cybersecurity, social-good or policy capability follows
from these DSL results. Those application evaluations and the neural
compounding/common-ancestor RSI requirements remain open.

## Research grounding

[Stitch](https://arxiv.org/abs/2211.16605) is relevant prior art for corpus-based
DSL library learning, and [Repo-To-Skill](https://arxiv.org/abs/2609.02749)
illustrates reusable research skills. These comparisons do not validate our
method. The September 3 [SkillRevise revision](https://arxiv.org/html/2606.01139v4)
also documents execution-linked candidate records and frozen principle banks.
Scope of reading and limits: `research-library-update-2026-09-16.md`.
