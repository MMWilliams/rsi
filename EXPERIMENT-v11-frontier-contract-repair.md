# V11: verified-frontier distillation after DSL contract repair

Status: preregistered before V11 bank generation. V9b completed all decisions but
its publication audit failed because the strict host oracle and permissive
published interpreter disagreed on malformed or noncanonical model programs.
V11 is a fresh study; it does not edit, pool, or reinterpret V9b.

## Contract repair

The canonical generated DSL grammar is the benchmark contract. The independent
oracle rejects noncanonical match sides such as `End` and trailing commas before
closing parentheses. The independent auditor uses the strict oracle for pass@k
reconciliation, verified frontier grading, and visible-behavior diversity. The
published parser remains available for canonical syntax and parseable-program
counts, but permissive fallback behavior is not a correctness definition.

The repair was regression-tested. The full project suite passed 84 tests. V9b's
sealed archive remains unchanged and its detailed neural outcome remains
unverified.

## Frozen setup

Use the V9b design with generation batch size 32, model Qwen3-0.6B revision
`c1899de289a04d12100db370d81485cdf75e47ca`, rank-8 q/v LoRA, three training
seeds (17, 29, 43), two rounds, four arms, 64 samples per task, and the same
training and admission settings. Use a fresh bank seed 9162612. Exclude every
template in all prior protected banks, including V9b, V10, and fixtures. Search
uses the frozen baseline and corrected filters, common macros, and budget 128.

Bank counts are harvest 96 each round, validation 32 each round, and final 64;
each task has three visible and thirteen hidden examples. Search receives only
task ID and visible examples. Hidden examples remain host-owned. Final scoring is
deferred until every optimization decision closes.

The four arms are baseline-selected, corrected-selected, corrected-first-verified,
and corrected-frontier. Every arm/seed starts from the audited common bootstrap.
Each update draws four anchor and four cumulative harvested examples, uses 48
optimizer steps, and is retained only when the admission bank loses no earlier
solved task, loses neither pass@1 nor pass@64, and strictly improves one of them.
Rejected checkpoints are restored with exact tensor hashes.

## Measurements and advancement screen

Report per-task and mean neural pass@1/4/8/16/32/64, distinct canonical programs,
visible behavior diversity under the strict oracle, parseable fraction, admission
decisions, all losses/gains, and full search/training/sampling/oracle/audit costs.
Never relabel deterministic search coverage as neural pass@k.

Primary contrast: corrected-frontier versus corrected-selected, selected round-two
pass@64. Advance only if the mean contrast is positive, positive in at least two
of three training seeds, corrected-frontier is above both frozen bootstrap and
unadapted base, and its round-two mean is no lower than round one. This is an
engineering screen, not a significance test or an RSI criterion.

## Audit and failure handling

Snapshot all source, protocol, configuration, bank, oracle, auditor and model
inputs before generation. Journal request hashes, exact replays, hidden grading,
training draws and losses, checkpoint lineage, admission reasons and costs. The
auditor regenerates banks, reexecutes searches, verifies strict-oracle scores and
behavior diversity, reconstructs all decisions, checks source hashes, and refuses
publication if any contract mismatch remains. Preserve failures and never reuse
a run ID. A passed audit is required before interpreting V11.

This study tests one transfer component in a bounded DSL. It does not establish
recursive self-improvement, application-domain capability, or all-input semantic
correctness.
