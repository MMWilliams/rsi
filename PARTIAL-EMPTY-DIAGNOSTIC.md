# Source-only primitive-filter and solution-frontier diagnostic

Written after the complete v7 single-fragment audit found zero opportunities.
Code inspection identified a different issue: `atom_pool` drops an atom if it
returns an empty string on any visible example. The task generator permits such
atoms inside nonempty concatenated outputs. Removing them can eliminate visible
solutions. This is a concrete hypothesis to measure, not yet a verified cause
of the recorded failures.

Use all 576 archived v7 source-development tasks and their original parent
settings/libraries. No transfer, admission or final evaluation; no new training.
Compare the cost-reopening baseline with a filter that allows empty outputs on
some visible examples but still drops pieces empty on every visible example.
Change nothing else: same position/token vocabulary, four-atom limit, heuristic,
library and 128-expansion ceiling. A separate diagnostic kernel keeps all
historical worker behavior intact. Require baseline output identity with the
existing reopening kernel and exact replay for both variants.

For each variant, exhaustively check **visible-example reachability within its
filtered pool** using dynamic programming over prefix-length vectors and total
primitive atom count. A representative for each (visible output vector, minimum
atom length) suffices for visible reachability, not hidden generalization. Keep
a witness and verify it independently. This separates representational failure
under the filter from bounded search failure. Record all states/edge checks.
The result is not a proof about all programs or all inputs.

Also retain the unique, cost-ordered solution frontier found inside the same
search budget, capped at 64 programs for reporting. Grade candidates only after
search closes, using both host and published interpreters on source examples.
Report selected-program correctness and deterministic search coverage at
k=1,4,16,64. These correlated, deterministic frontiers are **not IID model
samples**, so do not apply the neural pass@k estimator or claim neural gains.
The oracle observes outcomes; it does not alter the search order.

Primary comparisons: changed visible reachability, visible fits and selected
program correctness at matched expansion ceilings. Secondary: frontier coverage
and oracle-verified programs discarded by choosing only the first candidate.
No tuning after results. Measure primitive/expansion charges, replay, frontier
grading and reachability work separately. Archive raw outputs, witnesses, code,
input hashes and all failure records. This source-only diagnostic cannot promote
a new kernel or establish RSI without prospective fresh-task validation.
