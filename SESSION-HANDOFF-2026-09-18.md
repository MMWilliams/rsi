# RSI research handoff — 2026-09-18

Status: experiments stopped and progress saved. The overall RSI goal remains open.

## Current conclusion

The strongest supported evaluator seed for the tested synthetic familiar/shifted AST contract is:

1. Task-level listwise ranking as the evaluator training objective.
2. Dual-specialist top-100 confidence routing as the lower-cost fallback.
3. Exact output checks as optional, explicitly costed evidence-gathering actions.
4. External oracle, hidden examples and sealed test banks outside the editable loop.

This is an evaluator seed, not a demonstrated recursively self-improving improver.

## Validated evidence

- Task-level listwise evaluator: independent 48-bank replication scored 185/384 versus 173/384 for candidate-level BCE trained on the same 112,610 acquired labels. The objective replication gate passed. Replay audit passed.
- Dual-specialist evaluator: 85/192 on the tested mixed AST transfer, versus familiar-only 64 and shifted-only 43. It remains the lower-cost operating fallback.
- Exact output sensor: useful checks exist, but the learned allocation policy did not beat fixed entropy or random at the 96-call budget. All sensor promotion gates failed.
- Candidate stacking and shortlist width: useful exploratory edits, but integration and feedback gates failed.
- Direct parent-to-child improver: admission passed, but later child scored 340/576 versus initial 342, scrambled 341, duplicate 339 and fixed interaction-10 343. Later-minus-initial interval was -6 to +2. Recursive improver-growth gate failed.

## Important caveat

The earlier 24-bank sensor run used a shared preparation function that read true probe outputs before policy freeze. A public-only reconstruction reproduced all frozen choices without those outputs, proving functional choice independence, but literal prospective timing was violated. The output-blind preparer is now available and must be used for future sensor and parent/child runs.

## Primary reports

- `CROSS-FAMILY-META-IMPROVER-RESULTS-2026-09-18.md`
- `TASK-LISTWISE-TOP200-RESULTS-2026-09-18.md`
- `LISTWISE-BUDGETED-SENSOR-RESULTS-2026-09-18.md`
- `CANDIDATE-STACKING-FEEDBACK-RESULTS-2026-09-18.md`
- `SELECTIVE-WIDTH-FEEDBACK-RESULTS-2026-09-18.md`
- `SEED-IMPROVER-EVIDENCE-LEDGER-2026-09-18.md`

## Measurement and design notes

- `INTELLIGENCE-GROWTH-MEASUREMENT.md`
- `SEED-IMPROVER-CURRENT-DESIGN-2026-09-18.md`
- `.claude/TODO.md`
- `EXPERIMENT-task-listwise-top200-replication.md`
- `EXPERIMENT-listwise-budgeted-sensor-transfer.md`
- `EXPERIMENT-cross-family-meta-improver-transfer.md`

## Key audited artifacts

- `runs/task-listwise-top200-replication-20260918/audit.json`
- `runs/listwise-budgeted-sensor-transfer-20260918/audit.json`
- `runs/listwise-budgeted-sensor-transfer-20260918/public_nonleakage_addendum.json`
- `runs/cross-family-meta-improver-transfer-20260918/audit.json`
- `runs/cross-family-meta-improver-transfer-20260918/summary.json`
- `analysis/public-ast-probe-preparer-equivalence-20260918.json`
- `analysis/seed-improver-evidence-ledger-20260918.json`

## Reusable code

- `public_ast_probe_prepare.py` — output-blind public preparation path.
- `task_listwise_top200_development.py` — listwise/BCE evaluator training.
- `task_listwise_top200_transfer.py` and `task_listwise_top200_replication.py` — frozen evaluator transfer tests.
- `listwise_budgeted_sensor_transfer.py` — sensor allocation test; historical timing caveat documented above.
- `cross_family_meta_improver_transfer.py` — bounded parent/admission/child test.
- `seed_improver_evidence_ledger.py` — evidence ledger generator.

## Remaining tasks

1. Build a wider descendant-aware edit catalog: listwise objective, candidate generation/search, shortlist width, output sensor and rollback.
2. Record immediate edit gain, harm, acquisition cost, deployment cost and descendant gains separately.
3. Use `public_ast_probe_prepare.py` so no true output is read before allocation freeze.
4. Run a new protected parent/admission/child test across an independent mechanism set.
5. Require the later child improver to beat initial, scrambled, duplicate and strongest fixed schedules at matched source and deployment budgets.
6. Keep evaluator improvement, improver improvement and recursive child-improver improvement as separate gates. Do not mark the RSI loop successful from solver accuracy alone.

No process is intentionally left running.
