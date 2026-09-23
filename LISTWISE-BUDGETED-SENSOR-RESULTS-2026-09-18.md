# Budgeted external sensor after task-level ranking

**Result:** A true output check helped the strong listwise evaluator, but the feedback-trained task allocator did **not** pass any predeclared growth or integration gate. The later logistic selector scored 99/192 with 96 output calls, versus 97 for its early checkpoint, 98 for fixed predicted-probe entropy, and 100 for one seeded random control at the same call budget. The result is audited; keep the sensor action, not this learned allocation policy.

## Experiment and cost

The [frozen protocol](EXPERIMENT-listwise-budgeted-sensor-transfer.md) used 24 new eight-task familiar/shifted AST banks. All arms shared the frozen later listwise top-200 ranker, candidate pools, predicted probe outputs and four simulated deployment output calls per bank. Early query-value models trained on 192 opened task effects (six useful checks). Later models added 384 opened effects (22 useful checks); scrambled and duplicate-history controls held model class and row count. The learner saw 27 public features, including ranker confidence and predicted output partitions. The allocation function was given no true target output, task family or hidden correctness label. A host-preparation timing flaw, described below, prevents claiming that true outputs were first read only after allocations froze.

| Policy | Correct / 192 | True output calls | Useful checks selected |
| --- | ---: | ---: | ---: |
| No query | 91 | 0 | 0 |
| Early logistic | 97 | 96 | 6 |
| Early HGB | 97 | 96 | 6 |
| Later logistic | 99 | 96 | 8 |
| Later HGB | 99 | 96 | 8 |
| Scrambled-added-feedback HGB | 98 | 96 | 7 |
| Duplicate-history HGB | 97 | 96 | 6 |
| Fixed predicted-probe entropy | 98 | 96 | 7 |
| Fixed low ranker margin | 97 | 96 | 6 |
| Seeded random | **100** | 96 | **9** |
| Query every task | 103 | 192 | 12 |
| Retrospective best four per bank | 103 | 96 | 12 |

Every arm also used 113,958 common specialist/listwise candidate scores and 761,024 public candidate-output prediction cells; the [manifest](runs/listwise-budgeted-sensor-transfer-20260918/manifest.json) records preparation time. The measurement host evaluated all 192 true probe outputs to score every arm and the hindsight ceiling. Each selective *simulated deployment* arm is charged 96 output calls. Source effect acquisition required 576 earlier task outputs and externally verified zero/one choices, in addition to the ranker's prior 112,610 candidate-label acquisition. These costs are not interchangeable.

The later selector's +8 over no-query had paired bank interval +3 to +14 but appeared in seven banks; the sensor-integration gate required eight and failed. Later minus early was +2, interval -3 to +7; later minus fixed entropy was +1, interval 0 to +3; later trailed the random control by one. The incremental and fixed-policy gates failed. None of the 12 target query edits was harmful, but the sparse 12/192 positive rate limited allocation headroom. The later policy left four useful checks uncaptured; the random control left three.

The [post-audit forecast diagnostic](analysis/sensor-effect-forecast-diagnostic-20260918.json) also fails to establish a clearly better *effect evaluator*. Later HGB's Brier error improved only from 0.06010 to 0.05889; a scrambled-added-feedback HGB scored 0.05826 and had higher average precision (0.1146 versus 0.1010). Later logistic selected two more useful checks than early, but its mean predicted positive probability was 0.296 against an actual 0.0625 rate, reflecting its class-balanced training rather than calibration. These are descriptive diagnostics, not a new promotion gate.

## Replay and interpretation

The [audit](runs/listwise-budgeted-sensor-transfer-20260918/audit.json) passed after rebuilding 192 tasks, six source models from 576 effect rows, 761,024 predicted output cells, 1,152 target forecasts, all frozen allocations and 95,128 exact candidate labels. The public feature contract also reproduced the archived 27 features on an audited task before target preparation.

**Protocol timing deviation:** The reused host preparation function populated a `probe_output` field for every task before policies froze. The selector received a copy with that field removed. A separate [public-only reconstruction](runs/listwise-budgeted-sensor-transfer-20260918/public_nonleakage_addendum.json) rebuilt all 192 old-ranker orders, probe locations, 27-feature rows, forecasts and allocations from `id`, `seed`, `visible`, candidate pools and predicted candidate outputs, without handing true outputs, family or hidden labels to those functions. It passed, establishing *functional independence* of the choices from the early host reads. The literal frozen protocol's no-pre-freeze-read condition was still violated, and the original replay audit did not test that timing condition. Treat this run as a retrospective simulation with a validated nonleaking choice path, not a strictly sealed prospective query run. Future runners must keep true outputs unaccessed until allocations freeze.

The replacement [output-blind preparer](public_ast_probe_prepare.py) now reads only visible examples and offered probe input strings before freeze. Its base/wide pools, 34,224 predicted output cells, old ranker orders and probe locations matched eight archived audited tasks exactly in an [equivalence check](analysis/public-ast-probe-preparer-equivalence-20260918.json). It will be the required preparation path for the next prospective sensor test; the archived run's timing deviation remains part of its record.

Top-200 reachability was 107/192. Listwise without a query selected 91; querying every task selected 103. Thus a true output check closed 12 of 16 reachable ranking misses, leaving four. At the 96-call budget, even hindsight could add only 12, and random captured nine on this draw. The action is useful, but this fixed task distribution leaves little reliable room for a learned selector to beat strong simple controls. This does not show an improver becoming better at improving itself.

The seed-improver experiment needs more varied, consequential edit types and independent mechanisms: candidate generation/search, task-level ranker training, shortlist width, exact sensor allocation and rollback. Test predicted versus realized *future* edit effects and whether later inherited state creates a stronger child improver from the same base on a second untouched bank. Keep the exact oracle and hidden banks outside every editable component.

Raw evidence: [opened sensor effect matrix](analysis/listwise-sensor-edit-diagnostic-20260918.json), [opened equal-call screen](analysis/listwise-sensor-allocator-development-20260918.json), [target outcomes](runs/listwise-budgeted-sensor-transfer-20260918/results.json), [runner](listwise_budgeted_sensor_transfer.py).
