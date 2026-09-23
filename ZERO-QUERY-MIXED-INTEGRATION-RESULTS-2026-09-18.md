# Mixed zero-query evaluator integration: fresh transfer result

## Decision

Both prospective gates **failed** on 24 untouched mixed AST banks (192 tasks). The later public-feature route selected 45 correct programs with zero external output calls, versus E0 at 24, always using the shifted evaluator at 40, and a pooled candidate ranker at 33. Its +5 over always-shifted appeared on nine positive and four losing banks, with a paired interval **-3 to +13**; the integration gate required at least twelve positive banks and an interval above zero. It met the familiar and shifted subgroup limits, but that does not rescue the failed gate.

The direct paired-effect controller scored 43 before and 44 after adding 192 verified mixed edit-effect rows. Later-minus-earlier was **+1**, interval **-2 to +4**; later-minus-scrambled and later-minus-duplicate were each +3, intervals **-1 to +7**. Its predeclared improver-growth gate failed. Thus the prior shifted-task incremental evaluator gain remains valid, but this test does not show an improved general seed or a positive feedback loop in the improver.

The independent reconstruction audit **passed**: it regenerated all 192 tasks, 480 source effect rows, 771,952 predicted probe-output cells, 96,494 final candidate labels, and every frozen policy choice. See `runs/zero-query-mixed-integration-transfer-20260918/audit.json`, the frozen protocol `EXPERIMENT-zero-query-mixed-integration-transfer.md`, and complete paired results in the run's `results.json`.

## Same-bank policies

All policies used the same V67/V73 widened candidate pools and made no external output calls for this outcome. Task type appears only in source training labels or the unavailable type-oracle ceiling; target controllers used public visible examples and candidate statistics. The pooled ranker used 56,276 earlier familiar and 28,472 shifted candidate labels. The early controllers had 288 prior task records; later controllers added 192 verified mixed records. Scrambled and balanced duplicate-history controls preserved record counts.

| First-choice policy | All 192 | Familiar 96 | Shifted 96 |
|---|---:|---:|---:|
| E0 | 24 | 15 | 9 |
| Always shifted AB | 40 | 4 | **36** |
| Single pooled ranker | 33 | **20** | 13 |
| Earlier public-feature route, threshold 0.6 | 40 | 8 | 32 |
| Later public-feature route, threshold 0.6 | **45** | 13 | 32 |
| Balanced duplicate-history public route | 44 | 12 | 32 |
| Earlier paired-effect route | 43 | 8 | 35 |
| Later paired-effect route | 44 | 9 | 35 |
| Unavailable true-type route between E0 and AB | 51 | 15 | 36 |

The later public-feature route exceeded E0 by 21 (17 positive, zero losing banks; interval +15 to +27). It exceeded its own earlier checkpoint by five, but only four banks improved, and it exceeded its balanced duplicate-history control by only one (interval -2 to +4). This controller predicts task type; its later gain is not evidence that it learned edit effects. The paired-effect controller is the relevant improver test and failed.

## Failure dissection

The full pool held a final-correct program for **98/192** tasks; the old top 100 held one for **85**. AB fixed 29 E0 errors and caused 13 new errors, all harms on familiar tasks. The pooled ranker fixed 16 AB errors on familiar tasks but caused 23 new errors on shifted tasks. A hindsight switch between E0 and AB would solve 53; adding pooled as a third available choice raises that ceiling to **61**. Even those three choices miss 24 tasks whose top 100 contains a correct program, and 13 reachable tasks have no correct candidate in the top 100. These ceilings are diagnostic, not deployable policies. See `analysis/mixed-zero-query-failure-diagnostic-20260918.json`.

An exploratory post-test recombination using the frozen public-feature decision to choose AB or pooled instead of AB or E0 scored 48; the balanced duplicate-history router scored 50. These numbers were calculated after opening target labels and are **not** fresh evidence. They motivate a new three-action edit catalog with verified effects for each action, common candidate pools and a protected parent-to-child comparison. A later controller must beat its earlier self, scrambled feedback, and duplicate history on untouched banks before calling the improver better.

The run generated 27,320 base candidates and 69,174 added AST candidates. Preparing public records computed 771,952 candidate probe-output cells; each of A, AB and pooled scored 19,110 candidates. These costs are charged separately from zero external output calls. Results concern a synthetic AST task bank, not the stated research, cybersecurity, social-good or policy applications.
