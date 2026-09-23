# Top-three matched pilot

The fixture-sized shared-bank pilot is archived at `runs/top3-pilot-20260917`
and passed its audit (24 sealed artifacts, six journal events, regenerated
banks, and result-hash checks).

The pilot used six development, six admission, and eight final tasks from one
`mutation_transition` bank. V67's frozen and evolved AST rankers each solved
2/8 final tasks. V72 and V73 each solved 0/8. Because the bank's mechanism was
not the native target family for all three systems, these scores are an
interface smoke test, not a recommendation comparison. The result shows that
the versions cannot be stitched by simply placing their native candidate
generators on one arbitrary domain.

## Required next design

The ten-version comparison needs a common candidate envelope (`program`,
visible behavior signature, cost, provenance, required operations and
complexity), a mixed mechanism bank, and a task router that gives every module
the same visible examples and opportunity budget. Each module must pass the
same admission gate; final scoring stays on hidden examples. Without that
adapter layer, a stitched score would measure domain compatibility rather than
recursive improvement.
