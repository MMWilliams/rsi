# V9b semantic mismatch characterization

Status: posthoc characterization of the sealed V9b archive. It does not amend
the run, change its scores, or turn the failed publication audit into a passed
study.

## Finding

The 67 saved sample payloads contain 198,656 raw outputs. Comparing the output
programs against the published interpreter and the strict host oracle gives:

| Published interpreter | Host oracle | Outputs |
|---|---:|---:|
| incorrect | incorrect | 172,879 |
| incorrect | correct | 3 |
| correct | correct | 25,774 |

There were no outputs the published interpreter marked correct while the host
oracle rejected. The three oracle-only accepted outputs use a trailing comma in
`Concat('-', '.',)`. Python's AST accepts the comma; the published DSL parser
rejects it. This is a grammar mismatch and means those outputs must not be
treated as valid training targets for the published DSL.

There were 106 visible-output vector disagreements. Two contain the exact
`M(WORD,1,End)` pattern that caused the audit assertion. The remaining cases
include malformed or noncanonical model strings such as unsupported match-side
names. They were rejected by the strict oracle but received different behavior
from the permissive published interpreter. The behavior disagreement is therefore
larger than the full-correctness disagreement.

## Decision

The canonical generated DSL grammar is the benchmark contract. The independent
oracle now rejects trailing commas before closing parentheses while retaining its
independent implementation. It already rejected noncanonical match sides such as
`End`; the published interpreter's fallback behavior for any side other than
`start` is not accepted as benchmark semantics.

Two regression tests cover trailing commas and uppercase `End`. The V9b source
snapshot remains frozen and its neural result remains unverified. A fresh neural
run must snapshot the updated oracle, auditor and protocol, regenerate excluded
tasks, and pass the full independent audit before any pass@k or admission result
is promoted.

## Limits

This scan covers saved sample payloads, not every possible program. It does not
recompute V9b's neural selection or train on corrected labels. The 106 visible
behavior disagreements could affect diversity summaries and potentially other
derived metrics; no changed V9b score is published. The fix is a benchmark
contract repair, not evidence of model or improver improvement.

Evidence: `runs/frontier-distillation-20260916-v9b/` and
`analysis/v9b-semantic-mismatch-20260916.json`.
