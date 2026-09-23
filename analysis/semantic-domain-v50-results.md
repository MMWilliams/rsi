# V50 shifted semantic operator transfer

Status: audited two-seed result. V50 changes the task domain so variable-length delimiter transformations cannot be represented reliably by the original fixed-position DSL. The learner searches a bounded visible-only invention metalanguage, infers `Before`/`After` operators from verified training tasks, and applies the inferred catalog to fresh tasks.

| Seed | Baseline development | Baseline admission | Baseline final | Invention final |
| --- | ---: | ---: | ---: | ---: |
| 2026091900 | 16/24 | 13/24 | 14/24 | 23/24 |
| 2026091901 | 17/24 | 18/24 | 16/24 | 23/24 |

The inferred operator catalog contained `before` and `after`, recovered from 43/48 and 47/48 verified training tasks. Across both fresh banks, semantic invention improved final performance from 30/48 to 46/48. This is the strongest current evidence that expanding the hypothesis language can create transferable capability under distribution shift.

It is not yet proof of open-ended RSI: the semantic metalanguage, task generator, operator families, and verifier were researcher-authored; only operator instances were inferred. The next requirement is autonomous invention of the operator schema itself, followed by transfer to a second independently specified domain.

Both runs passed independent audits, replaying 288 evaluation rows and checking 19 sealed artifacts per run.

Artifacts: `runs/semantic-domain-v50-20260918/` and `runs/semantic-domain-v50-20260919-seed01/`.
