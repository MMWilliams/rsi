# V56 representation selection on a disjoint alphabet

Status: audited two-seed result. V56 keeps delimiter training in the original ASCII domain but evaluates on a disjoint transition domain using Greek letters and Arabic-Indic digits. A preregistered representation controller chooses between raw ordinal ranges and structurally induced character-family predicates using development/admission performance before final evaluation.

| Seed | Baseline final | Raw ordinal final | Structural-family final | Selected representation |
| --- | ---: | ---: | ---: | --- |
| 2026091912 | 0/24 | 0/24 | 24/24 | structural family |
| 2026091913 | 0/24 | 0/24 | 24/24 | structural family |

The same pattern held on development and admission: baseline 0/24, raw ordinal 0/24, structural family 24/24 on both seeds. The controller therefore selected the structural family arm twice without looking at final results. The structural vocabulary contained three induced category families and verified all 48 delimiter-training tasks.

This is a stronger transfer test than V55 because the evaluation alphabet is outside the ASCII ranges learned from training. It shows that representation selection can recover a transferable observation language when a lower-level candidate fails. It is not yet open-ended RSI: the candidate structural feature language still exposes Unicode category, the task domain is synthetic, and the controller selects among researcher-authored representation families.

Both independent audits passed, replaying 216 evaluation rows and checking 21 sealed artifacts per run.

Artifacts: `runs/representation-selection-v56-20260918/` and `runs/representation-selection-v56-20260919-seed13/`.
