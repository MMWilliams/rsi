## C046 - Test the recommended trio and expose interface mismatch

- V67/V72/V73 were run on one fresh shared `mutation_transition` pilot bank with equal small budgets. The audit passed.
- V67 solved 2/8 final tasks; V72 and V73 solved 0/8. The bank was outside the native target assumptions of the latter two arms, so the pilot is an interface smoke test and not a ranking result.
- Before stitching ten versions, define a common candidate envelope, mixed-family bank, shared admission gate, and leave-one-arm-out controls. See `EXPERIMENT-stitch-ten.md`.
