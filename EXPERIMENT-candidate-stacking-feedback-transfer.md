# Candidate stacking and incremental feedback: frozen fresh test

Date: 2026-09-18. Written before target generation or target labels are opened.

## Question

Can a candidate-level evaluator combine two validated specialists better than the current confidence route, and does adding verified candidate feedback produce a better evaluator checkpoint? A second question is whether that added scoring work beats a fixed shortlist-width allocation at a similar specialist-score budget. This is an evaluator edit and a candidate for an improver catalog, not yet a recursive-improver test.

## Frozen data and arms

Early stacked ranker: histogram gradient boosting with 15 leaves, 80 minimum leaf samples, 100 iterations, learning rate .05, L2 1, seed 0. Its input is the 184 public structural/ranking features plus familiar/shifted probabilities and seven public meta features. It trains on 38,058 exact top-100 candidate labels from the first two audited mixed panels (384 tasks). Later uses the same rule plus 19,092 labels from a third audited panel (576 tasks total). All training labels are from previously opened banks. Scrambled control permutes added labels within task; duplicate control replaces the added 192 task groups with 192 sampled early groups. All model files are frozen before target preparation.

Target: 24 new deterministic mixed banks, seeds 905100–905123, four familiar and four shifted AST tasks per bank (192 total), generated with the same verified candidate pipeline as the dual-specialist transfer. Source, target, candidate generator, old ranker, two specialist model files and external exact interpreter are separate. No target family or hidden output enters a model choice.

Report zero-query top-choice correctness, subgroup correctness, top-100 reachability, bank paired intervals, candidate scores, source labels and generation/preparation costs for:

- Fixed dual-specialist confidence top-100 and fixed candidate-mean top-100.
- Early, later, scrambled, duplicate stacked top-100.
- Later pooled structural top-100 as a singular-ranker control.
- Fixed dual top-200 and later stacked top-200 as shortlist controls.
- Fixed shifted-priority dual shortlist, widening four of eight tasks per bank to 200; same approximate score budget as stacked top-100, with exact counts reported.

The evaluator-growth gate requires later stacked top-100 to beat early, scrambled, duplicate, fixed dual and fixed candidate mean by at least five tasks each; its paired 95% bank-bootstrap lower bound must exceed zero against early and fixed dual, with at least eight positive banks against early. Integration promotion additionally requires later to beat fixed dual by at least eight, a positive lower bound, at least twelve positive banks, and no familiar/shifted subgroup loss larger than eight versus that subgroup's specialist. Audit must pass. Report comparisons to fixed selective-width separately; candidate scores are not equal to total compute. No tuning on target outcomes.

## Freeze and replay

Store and hash protocol, runner, source/model files, sealed target, pools, public records, per-policy choices, allocations and costs before hidden labels are scored. Score all target candidates using only the external exact interpreter. Replay target generation, model predictions, choices and all final labels for audit. Acquisition, model training, old ranking, candidate generation, output prediction and specialist/meta inference are distinct resource entries.
