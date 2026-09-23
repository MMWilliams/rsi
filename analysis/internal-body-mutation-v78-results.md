# V78: typed mutation of retained macro bodies

## Research question

Can retained executable macros improve themselves through direct typed edits to their internal stack bodies, rather than only through independent proposal or output-level composition?

## Protocol

Development tasks used `macro_transition`; admission and final tasks used the separate `novel_operator_transition` family. The mutation engine started from each retained body and applied bounded constant edits, binary-operator replacements, and stack-balanced raw-bit grafts. Candidate selection used visible examples only. Legacy ordinal, direct grammar, and unmodified macro replay were controls.

## Findings

| seed | arm | development | admission | final |
|---:|---|---:|---:|---:|
| 2026092701 | legacy | 6/24 | 9/24 | 2/24 |
| 2026092701 | direct grammar | 24/24 | 18/24 | 9/24 |
| 2026092701 | mined macro | 24/24 | 18/24 | 9/24 |
| 2026092701 | internal mutation | 6/24 | 9/24 | 2/24 |
| 2026092702 | legacy | 6/24 | 8/24 | 8/24 |
| 2026092702 | direct grammar | 24/24 | 19/24 | 16/24 |
| 2026092702 | mined macro | 24/24 | 19/24 | 16/24 |
| 2026092702 | internal mutation | 6/24 | 8/24 | 8/24 |

Internal mutation matched the legacy arm on both seeds and was never eligible for selection. Directly editing retained bodies therefore damaged the useful representation rather than extending it.

## Interpretation

This is a negative but important RSI result. A mutable representation is not automatically an improving representation: without counterexample-guided fitness, parent protection, or a retention gate, local body edits destroy transfer structure. The result identifies the next engineering requirement—mutation must be evaluated as a lineage with protected parents and selected through held-out admission.

## Limitations

The mutation vocabulary, edit bounds, graft grammar, family boundary, visible alignment, and admission gate remain researcher-authored. The experiment uses one mutation generation and does not yet implement lineage-level evolutionary credit or rollback. It is bounded self-editing evidence, not open-ended RSI.

## Verification

Both independent audits passed, replaying 288 arm-task rows and checking 22 sealed artifacts per run. Archives: `runs/internal-body-mutation-v78-20260927` and `runs/internal-body-mutation-v78-20260928`.
