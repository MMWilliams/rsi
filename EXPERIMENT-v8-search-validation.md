# V8: prospective validation of search filtering and budget allocation

Written before generating or scoring the fresh bank. This follows the audited
source-only filter diagnostic; it is not a recursive-improvement experiment.

## Fixed design

Six new generator seeds: 269, 281, 293, 307, 317, 331; 96 tasks each. Use the
published string DSL, three visible and thirteen hidden examples, maximum four
atoms. Exclude reference templates in every prior archived protected bank and
between the six new seed groups. Record exclusions, origins, seeds and generator
attempts. This conditions the task distribution on prior exclusions; these are
fresh groups, not six independent neural training runs.

Use BASE_CONFIG and the same 13 common macros from v7. No learned proposal,
training, adaptive tuning, or outcome-dependent stopping. Freeze source files
before generating the bank. Search sees only task IDs and visible examples.
Complete every search and exact replay before grading the first hidden outcome.

Compare baseline and partial_empty diagnostic kernels at expansion ceilings
32, 64, 128 and 512. Alternate which filter executes first by task index;
retain each call's wall and CPU time. Replay is a separate measured call and
must reproduce both the payload and the complete diagnostic data exactly.

Construct a fixed mixture from baseline@64 and partial_empty@64. Deduplicate
their recorded candidates by program, choose lowest cost for duplicate entries,
and order by (cost, program text length, program text). Keep the first 64.
This allocates a total expansion ceiling of 128 but pays for both pools.
Charge both searches; do not describe cached combination as free inference.

## Measures and decisions

Primary comparison: partial_empty@128 versus baseline@128, on first-choice
correctness and deterministic coverage@64. Declare the source gain replicated
only if both aggregate differences are positive and both differences are
positive in at least five of the six seed groups. This is an engineering screen,
not a significance test or an RSI criterion. Report all groups and paired task
wins/losses, including at the other budgets. No resampling to choose a winner.

Secondary: mixture@128 versus each single filter@128, and budget curves. Report
coverage@1/4/16/64, visible fits, verified-program count, expansions, primitive
executions, generated nodes, CPU/wall seconds, and grading/replay costs.
These correlated deterministic programs are not IID model pass@k samples.
No all-input semantic-equivalence claim follows from finite-example grading.

Equal ceilings are not matched actual compute. Report the full cost vectors;
do not turn a favorable point on one axis into a total-compute claim. Wall/CPU
measurements are host-specific and cannot be bit-exact replay criteria. The
mixture incurs additional atom-pool overhead. Model calls and training are zero.

The screen can justify the next controlled training experiment, not promotion
as a universally better default. Regressions, retention, equal-compute performance,
neural transfer and common-ancestor improver quality remain separate requirements.

## Evidence and failure handling

Archive frozen source/protocol/configuration, common macros, protected bank,
prior-template hashes, public requests, raw outputs/frontiers, separate replay
hashes/costs/timings, host grades, pairwise task IDs and all summary decisions.
Journals are durable and hash chained. A separate auditor verifies the archive,
recreates the fresh bank, reexecutes searches, reconstructs the mixture without
using its constructor, regrades with the published interpreter and independently
recomputes scores and the decision. Hashes do not authenticate a compromised host.

Keep failed runs; never overwrite a run ID. If implementation repair changes a
scored run, preserve it and label the repair/retest explicitly. Tests use fixed
synthetic fixtures before creating the bank. No full-loop or application-domain
claim follows from this component test.
