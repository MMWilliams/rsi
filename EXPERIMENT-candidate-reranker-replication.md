# Frozen candidate-reranker feedback replication

Frozen 2026-09-18 before generating seeds 902522-902533. This is a second, disjoint 12-bank panel of 48 synthetic tasks per bank. The source tasks, exact labels, models, structural features, old ranker, candidate pools, probe rule, and eight-call allocator are precisely those in `EXPERIMENT-candidate-reranker-transfer.md`; the four model files are copied byte for byte. The original panel is already opened and cannot validate a newly selected rule.

## Primary incremental checkpoint test

On the new panel compare E1 and E0 with no output calls on identical pools. Reuse the original predeclared promotion gate: E1-E0 >= 8 correct tasks, at least eight positive banks, at most two losing banks, exact paired bank-bootstrap lower endpoint > 0, E1 above the leaf-7 and scrambled controls, and E1 at least E0 with the same eight calls per bank. Report the bank differences, reachability and all resource counts even if the gate fails. A pooled 24-bank estimate and interval are descriptive only; it cannot replace the new-panel gate.

## Separate post-hoc hypothesis tested prospectively

The opened panels suggested routing public `self_edit_transition` tasks to the old ranker and all other tasks to E1. Freeze that exact rule here. Compare it with E1 on the new panel at zero calls and with the same eight-call locations, using paired bank differences and the same interval method. Treat the fallback as supported only if the new-panel zero-call gain is positive with a positive lower interval endpoint and the eight-call score does not regress. No additional family or task gate is selected after opening labels.

## Independence and cost

The fresh task outputs and final candidate labels remain sealed until tasks, candidate pools, model orders, output predictions, probe indices and call locations are persisted with hashes. Rebuild the original source and fresh task/pool/feature/prediction/label calculations independently. Charge historical source acquisition, new candidate generation, top-20 rescoring, predicted output cells and exact output calls separately. This tests evaluator feedback and a fixed rule; it is not an improver-child test.
