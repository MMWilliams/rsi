# Source-only search cost-relaxation diagnostic

Written after the frozen v7 study completed and its semantic audit passed.
Instrumentation found four cheaper routes discarded among 704 task evaluations
for all 44 actual source-library additions. The first 128 generic source
candidate evaluations (many no-ops) had found none; both diagnostic outputs and
the first instrumentation script are retained. This is a targeted correctness
investigation, not an independent replication or a final-bank improvement claim.

`rsi.search_reopen` corrects first-arrival cost suppression by tracking the best
cost per syntactic state, reopening strictly cheaper paths, resetting their
outgoing-edge progress and ignoring stale queue entries. It uses the original
atom pool and heuristic. This fixes a route-cost invariant; it does not make
bounded heuristic search globally optimal. The original worker remains pinned
to the original kernel, preserving the study and its historical controls.

Before adopting the new kernel, replay every recorded source fragment-addition
request under it and replay each corresponding parent request. These are the
44 source proposals already selected by the old policy, not newly selected
proposals or a simulated trajectory. Deduplicate identical public requests;
run each twice and require identical results. Grade on the archived source
development examples with both the published interpreter and independent host
oracle. No transfer or final task is evaluated. Report old/new parent and
candidate correctness separately, and candidate-minus-parent effects under
each kernel. No tuning or candidate substitution during the diagnostic.

Save every input/output, code snapshot, hash, timing and comparison in a fresh
archive. A changed output or restored cheaper route is not itself a capability
gain. A fresh prospective common-ancestor experiment remains necessary before
promoting library inheritance or claiming improved recursive behavior.
