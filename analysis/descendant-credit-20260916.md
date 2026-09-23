# Descendant credit: recorded signal and local decision influence

Archive `inheritance-20260916-v5`; independently re-audited. This is a retrospective diagnostic, not a new inheritance experiment.

| Trace group | Adaptive choices | Nonzero descendant term available | Local choices flipped by descendant term |
| --- | ---: | ---: | ---: |
| source | 432 | 20 | 0 |
| transfer | 288 | 82 | 2 |
| transfer/g0 | 72 | 0 | 0 |
| transfer/g3 | 72 | 7 | 0 |
| transfer/g6 | 72 | 41 | 2 |
| transfer/random | 0 | 0 | 0 |
| transfer/scrambled_g6 | 72 | 34 | 0 |

Source tables: 9/72 operator entries have descendant trials; 5 have a nonzero descendant gain sum.

## What the statistic means

Each accepted ancestor occurrence receives every subsequent selected candidate's admission gain, including rejected candidates. Multiple occurrences of one operator name receive repeated credit for the same later observation. These credits are dependent observations, not independent evidence or randomized attribution to an ancestor.

Removing a term from a recorded score holds the beta draw, available actions and prior choices fixed. After a changed choice, subsequent states, exclusions, tables and random streams may diverge. Therefore local flips do not estimate an ablated policy's final performance. In source calibration all twelve edits were evaluated; a changed proposal ordering alone does not change that generation's candidate set.

## Recorded credits

- source: 29 ancestor credits from 18 later decisions; 15 credits came from rejected candidates; 8 involved repeated operator names.
- transfer: 53 ancestor credits from 44 later decisions; 42 credits came from rejected candidates; 8 involved repeated operator names.

## Implication for the next improver test

Separate immediate-effect inheritance from descendant-credit inheritance in prospective common-ancestor forks. Run descendants from paired states with and without the earlier edit to test its contribution, holding downstream policy and budgets fixed. Report rejection and measurement uncertainty. A coefficient change alone cannot establish useful descendant knowledge.

Independent audit cost: 4.17 seconds. No live experiment source was changed. Full credit events, local sensitivities, hashes and audit results are in the adjacent JSON.
