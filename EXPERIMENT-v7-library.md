# V7: learned fragment proposals from the same solver ancestor

Written 2026-09-16 before generating banks or running this study. V6 did not
establish a useful context predictor. V7 tests a different intervention: adding
reusable program fragments to the existing amplifier, using only solutions
verified on separate harvest tasks. No weights are trained in this component
study. It is neither full RSI nor an unrestricted self-created edit language.

## Design

Six new sources (181, 193, 211, 223, 239, 251), each with six generations. Each
generation uses fresh 16-task harvest, development and admission slices. The
bank seed is 9162607. All prior archived template families are excluded; splits
are template-disjoint. A shared 192-task final bank is evaluated only after all
source and transfer optimization has closed. Three visible and thirteen hidden
examples per task; fixed 128-expansion ceiling, at most four primitive atoms.

The common starting solver is BASE_CONFIG with the same thirteen macros used
in v4/v5. The search implementation is unchanged. A four-atom entry in that
historical library is ignored by its existing macro parser; it is retained for
an identical ancestor, not described as an active learned fragment.

At every generation:

1. Search harvest tasks with the current solver and replay each request exactly.
   Keep only oracle-correct whole solutions as evidence. Extract distinct
   contiguous two- and three-atom fragments. Fragment provenance names the
   harvest request, task and whole-program hash. A fragment's source solution is
   verified; the fragment itself is not claimed to solve that task.
2. Rank remembered fragments not already in the solver library using public
   development examples only. Count tasks where the fragment's nonempty output
   is a substring of every visible target. Sort by descending count, distinct
   supporting certificates, atom length, then ascending fragment text. Only
   positive-compatibility entries qualify. No oracle development result enters
   this ranking. Record every score and charged fragment executions.
3. Propose two separate single-fragment additions to the same parent library,
   with a maximum of 32 library entries. Missing candidates become explicit
   no-ops and still receive evaluations. Score parent and both candidates on
   development tasks. Pick the larger gain, breaking ties by proposal index.
4. Score parent and the best candidate on the admission slice, even if gain is
   zero. Accept only strictly positive development gain and nonnegative admission
   gain. Retain both losing and rejected proposals. Search config stays fixed in
   library arms. Harvest memory grows even when the proposed change is rejected.

The source uses this loop with empty initial proposal memory. Transfer starts
from the **same original solver config and original active macro library in
every arm**. Only the improver's candidate memory varies: source g0, g3, g6, or
scrambled g6. Inherited fragments are candidates, not preinstalled solver code.
Every transfer arm gets six generations on identical per-source task slices.
All may learn from their own verified harvest. This tests a learned proposer
from a common artifact, avoiding attributing a preinstalled library to a better
improver.

Additional controls: `numeric_pair` proposes absolute-cost x0.65 and x1.4 with
the established bounds; `frozen_library` proposes two no-ops. Both run the same
harvest, memory extraction, visible ranking and evaluation schedule. They do
not install fragments. This fixed numerical pair was discovered as a strong
offline control in v6; these tasks are fresh.

Scrambled memory pools primitive atoms within each fragment-length bucket,
shuffles with Random(source_seed + 77007), and repartitions into fragments of
the original lengths. Support records explicitly carry `scrambled_from` so a
corrupted fragment is never represented as a verified source fragment. Merge
colliding fragments, preserve their provenance, and log original/resulting counts
and the complete construction trace. Empty or unchanged controls are reported.
This disrupts composition while retaining the same primitive atom multiset;
it is not guaranteed to destroy every useful fragment or preserve unique count.

## Costs and evidence

Every arm is charged the same source acquisition ledger as an informational
intervention, including g0/numeric/frozen controls that discard its contents.
Actual source work is executed once and shared. This does not compare the best
alternative use of the acquisition budget. Downstream arms have matched task
counts, candidate counts and expansion ceilings, not identical primitive work,
wall time or FLOPs. Report actual charged expansions, primitive work, oracle
upper bounds, visible ranking charges, worker time and whole-run time. No paid
model calls or neural inference/training. Prior common-library acquisition is
shared and identified, not silently claimed free.

Record source/config/bank hashes, exact requests, replay hashes, independent
grades, source certificates, ranked candidates, memory/library hashes, all
parameter/library diffs, per-task wins/losses, admission reasons and snapshots.
Independent audit must reconstruct memory provenance, scrambled controls,
rankings, proposal arithmetic, every admission, common starts, costs and final
cutoff. Retain failed attempts. No edits to snapshotted source during a run.

## Outcomes and screen

After all optimization closes, score the common ancestor and generation-3/6
solver snapshots for sources and every transfer arm. Primary outcome is final
accuracy after six transfer generations. Report g6-memory minus g0, g3,
scrambled g6, numeric pair and frozen library, paired by source and task.
Also report per-source contrasts, accepted edits, source/transfer learning
curves and cost ledgers. Shared final tasks and six sources limit inference.

Advance the mechanism only if all five mean primary contrasts are positive
and at least four of six sources have g6 strictly above both g0 and scrambled.
This is an exploratory component screen, not statistical proof of RSI. Macro
growth alone, accepted changes alone, or outperforming only the frozen control
does not satisfy it. Even success requires fresh replication, a stronger
acquisition-allocation control, neural compounding and application-domain tests.

## Prior work

[Stitch](https://arxiv.org/abs/2211.16605) learns abstractions from DSL program
corpora and compares against DreamCoder; our contiguous fragments are much
less expressive and are not a reproduction of its compression algorithm.
[Repo-To-Skill](https://arxiv.org/abs/2609.02749), September 2 abstract checked,
reports improvements from distilled repository skills with fixed downstream
backbone/harness/budget. Those are skill-augmented artifact gains, not evidence
for this common-ancestor improver test. Explicit reusable code is not novel
alone. Our test's outcome remains empirical.
