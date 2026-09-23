# Learned value of one verifier query: frozen transfer protocol

Frozen before generating seeds 902258–902263 on 2026-09-17.

## Evaluator and query budget

Use the fixed temperature-0.25 listwise ranker trained on 31,500 source candidate labels, the same two candidate sources capped at 128 each, one visible example, eight unlabeled probe inputs, and 15 final scoring examples. Six untouched 32-task banks cover stack, mutation, and self-edit transitions. No model weights or candidate sources change in this trial.

For each task, a public-input-only rule selects the probe with maximum output entropy among the ranker's top 16 candidates. A selected policy buys exactly one external oracle output on that input, filters the full candidate pool to programs matching it, then chooses the highest-ranked survivor. If no program matches, keep the original ranker choice. Each active policy receives **95 queries total across 192 tasks**. Query allocation and probe indices are frozen before any oracle probe output or final label is read.

## Policies and gate

- Learned query-value model: frozen 18-feature ridge predictor with penalty 10, fitted on 192 previously inspected development tasks and their verified one-query gains. Choose the 95 highest predicted gains.
- Fixed top disagreement: choose tasks by how often the ranker's top two candidates disagree across eight probe inputs; break ties by smaller top-two score margin and task ID.
- Fixed uncertainty: choose the 95 smallest top-two score margins.
- Deterministic random: choose 95 tasks by hashed task ID.
- No-query ranker as the zero-cost reference.

Primary endpoint: learned minus fixed top-disagreement final top-choice correctness. A supported learned evaluator-policy upgrade requires wins on at least five of six banks, a strictly positive exact six-bank resampling 95% interval, and higher aggregate accuracy than every fixed policy at the same 95-query budget. Report candidate reachability, per-family scores, query and candidate-execution costs, and any gain over no-query separately. A gain over no-query alone is not evidence that the learned allocation improved.

Prepare/score separation, source and runner hashes, and an independent reconstruction audit are required. The oracle output and final examples are external feedback; this is a synthetic finite-example test, not a universal semantic verifier or an improver-growth claim.
