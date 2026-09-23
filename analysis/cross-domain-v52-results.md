# V52 cross-domain generic-span transfer

Status: audited two-seed cross-domain result. The system learns the generic `Slice(boundary,boundary)` schema on delimiter tasks, then evaluates on a delimiter-free domain where useful boundaries are letter↔digit transitions.

| Seed | Fixed-DSL baseline final | Generic span final | Training domain | Evaluation domain |
| --- | ---: | ---: | --- | --- |
| 2026091904 | 19/24 | 24/24 | delimiter | letter/digit transition |
| 2026091905 | 22/24 | 24/24 | delimiter | letter/digit transition |

Across both cross-domain banks, generic span transfer reached 48/48 versus 41/48 fixed-DSL baseline. The learner verified all 48 delimiter-training tasks on both seeds; no named transition operator was present in the training protocol.

This is stronger than in-domain macro transfer: the same compositional schema transfers to a different boundary mechanism. It still does not prove open-ended RSI because the transition-boundary observation rule and the `Slice` algebra remain researcher-authored.

Both audits passed, replaying 288 evaluation rows and checking 22 sealed artifacts per run.

Artifacts: `runs/cross-domain-v52d-20260918/` and `runs/cross-domain-v52e-20260919-seed05/`.
