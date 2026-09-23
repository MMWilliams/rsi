# V23 active counterexample-guided synthesis

Status: audited interactive finding. The oracle-assisted arm is not passive RSI evidence.

## Protocol

The solver began with three visible examples. It proposed a CEGIS program, queried a hidden oracle only when that program failed on a held-out example, appended the first counterexample, and re-ran synthesis. Query budgets were 0, 1, 2, and 4 in V23-A, followed by 0, 1, and 2 in an independent V23-B replication. All arms used the same CEGIS substrate, budget 512, maximum six atoms, and visible constant synthesis. The query budget was selected using development and admission banks; the final bank was scored after selection.

## Result

| Oracle counterexample budget | V23-A final | V23-B final | Mean queries (A / B) |
| ---: | ---: | ---: | ---: |
| 0 | 15/24 | 18/24 | 0.00 / 0.00 |
| 1 | 23/24 | 24/24 | 0.38 / 0.25 |
| 2 | 24/24 | 24/24 | 0.42 / 0.25 |
| 4 | 24/24 | — | 0.42 / — |

The admission gate selected two queries in V23-A and one query in V23-B. The selected arms achieved 24/24 on both fresh final banks, compared with 15/24 and 18/24 for passive CEGIS. The extra queries were rarely needed: the selected arms averaged 0.42 and 0.25 counterexamples per task.

## Audit

The independent audits replayed 504 staged task evaluations in total (288 in V23-A and 216 in V23-B), regenerated every counterexample-guided trajectory, verified deterministic outputs and query counts, recomputed the query-budget selections, checked the journal bindings, and verified 42 sealed artifacts. Both audits passed.

## Interpretation

This demonstrates a compact interactive synthesis loop: counterexamples do more than rank a fixed hypothesis set; they change the synthesis state and expose previously invisible epsilon transitions. It is the strongest current capability result in the project, but it is not RSI. The loop depends on an external oracle, a fixed DSL, a fixed candidate grammar, and researcher-authored query and compute budgets. The next RSI-critical test is to retain what the interactive loop learns—new grammar rules, search policies, or reusable abstractions—and show that a later generation improves without continued oracle access.

Artifacts: `runs/active-cegis-v23-20260917/results.json`, `runs/active-cegis-v23-20260917/audit.json`, and `runs/active-cegis-v23-20260917/`.
