# Balanced edit calibration and common-ancestor transfer

Declared 2026-09-16 before generating or scoring v4 banks. The full objective remains system RSI; this component experiment addresses whether inherited improvement statistics are useful after collecting more balanced evidence. It is not a neural coverage or unrestricted self-rewriting experiment.

## Motivation and isolated change

The v2 source runs tried only 24 edits across 12 types. Some types were never tried and none had more than four trials. We cannot infer that effect-table inheritance is intrinsically ineffective from that assay. Change only source proposal coverage to all 12 existing edit types in each of six generations. The numerical edit language, search budget, table update/selection rule, and admission rule remain unchanged. No new selection algorithm is added. The current logging includes every attempted edit.

Three source seeds use disjoint 96-task development and 96-task admission banks. Each generation uses fresh 16-task slices and tries every initial edit once. This yields six source trials per operator (72 proposals per seed), with generation-3 and generation-6 snapshots. Those trials are not independent of evolving parent state; report that limit and the number of informative positive/negative effects rather than treating all proposals as equally informative.

## Direct improver test

For each of the three sources, transplant g0/g3/g6 tables, a deterministic permutation of g6 records, and an empty random-selection control into the identical BASE_CONFIG ancestor with the same initial catalog and common verified macro library. Each restart gets its own source-independent 96-task development and 96-task admission banks, shared across the five conditions. Six generations, two proposed edits per generation, fresh 16-task slices. Use the same seed within a paired comparison. Keep all decisions and candidate outcomes, including rejections.

Final evaluation uses 128 tasks shared across all conditions and sources. Close every optimization trajectory before inspecting final scores. Report each seed separately and paired differences. Check whether later tables produce larger gains relative to the identical ancestor and whether g6 beats scrambled and random controls. G0 is the empty adaptive table; avoid counting an identical second empty condition as independent evidence.

## Task and oracle boundaries

Generate fresh banks and exclude literal-scrubbed reference templates from all earlier local banks. Record exclusions and hashes; bank generation order and exclusions affect the distribution. Do not compare v4 absolute rates directly with v2. Source/transfer/final reference templates are disjoint. Worker requests contain task IDs and visible examples only. Keep the existing independent host oracle and bit-exact search replay. The boundary still does not sandbox arbitrary native code running as the same user.

## Compute and success claims

Transfer conditions get equal candidate counts, development/admission sizes, expansion limits and replay rules. Report actual logical expansions, primitive executions and elapsed time, including rejected candidates. Equal edit opportunities are not equal total compute. Source calibration is a separately reported acquisition cost; g0 and random do not become fully compute-matched merely because they share the study. This test isolates the table's downstream effect, conditional on acquiring it.

Prespecified primary contrasts: g6−g0, g6−g3, g6−scrambled, g6−random in final solve rate averaged across the three paired sources. Report per-source paired-task bootstrap intervals as descriptive, plus all three source-level differences. Three sources cannot establish a powered general claim. A positive result must be followed by fresh replication and compute-matched acquisition controls; a negative result redirects work toward the edit space, inference rule, or stronger evidence rather than proving RSI impossible.

Archive protocol/config/code, all banks, initial macros with provenance, every source and transfer trajectory, per-attempt events and costs, terminal status, and an artifact hash manifest. Independently regrade journaled solutions with the published interpreter, reconcile table updates from candidate outcomes, and link final scores to the frozen trajectory configurations. Run exactly once under this protocol; preserve failures and do not tune on final outcomes.

## Audit and accounting clarification before the run

Every evaluation now records its exact public request and cost delta. The auditor
reconstructs all table updates and admission decisions from independently regraded
outputs, checks shared ancestors and table transplants, and rejects any final
evaluation before optimization closes. A small temporary-bank fixture checks the
whole path; forged effect tables and premature final evaluation must be rejected
even after archive hashes are recomputed. Fixture outputs are not study results.

Operation counts are logical charges: cached primitive work is counted again for
replay, and oracle example counts are upper bounds when execution short circuits.
Worker elapsed time excludes host grading and journaling; whole-run elapsed time
includes those but excludes the later audit. Acquisition and downstream search
costs are reported separately. None is a claim of matched hardware compute.

## Research basis

[Huxley-Godel Machine](https://arxiv.org/html/2510.21614), abstract and introductory algorithm description inspected, motivates separating immediate solver performance from later improvement potential. We do not reproduce its clade estimator. [Generalized Agent Iteration, September 11 2026](https://arxiv.org/html/2609.13406v1), abstract/introduction inspected, motivates specifying the modifiable improvement mechanism and externally grounded evaluation separately. Neither source establishes novelty or expected success for this table-transplant experiment.
