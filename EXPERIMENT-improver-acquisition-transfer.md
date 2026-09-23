# Same-base improver acquisition transfer: frozen protocol

Frozen before generating new source or target banks on 2026-09-17. This tests
whether a feedback-acquisition rule improves a child evaluator at a fixed
candidate-label budget. It does not show that the acquisition rule itself
improves across generations.

## Development choice

On the already inspected 192-task source and 192-task target, each rule spent
exactly 7,000 candidate correctness labels. The fixed E0 structural evaluator
was the common starting point. Low-confidence source-task ranking produced a
child scoring 97/192, versus source order 91, uncertainty 93, small-pool 76,
random 64, and iterative low-confidence 90. This is development selection,
not transfer evidence. Low-confidence ranks each unlabeled source task by the
negative of E0's largest candidate probability, with task-ID ties. Candidate
pool size and features are public; oracle labels are opened only after a task
is selected. The last task may be partially labeled to spend exactly 7,000.

## Fresh same-base comparison

- Common base: E0 structural weights frozen in
  `analysis/mixed-evaluator-checkpoints.json`.
- New source: 192 tasks, seed 902209, cycling stack, mutation, and self-edit;
  one public example, eight probe inputs, 15 scoring examples. Candidate
  sources/caps are unchanged from the evaluator checkpoint study.
- New target: six independent 32-task banks, seeds 902210–902215, same
  mechanisms and candidate sources. No target labels inform child training.
- Each arm receives the same source candidate pools and exactly 7,000
  candidate correctness labels, each checked on 15 source scoring examples.
  Arms: source order, low-confidence, uncertainty, small-pool, deterministic
  random, and iterative low-confidence (three batches with retraining between
  batches). The last selected task can be partially labeled. Shared actual
  oracle computations are still charged to each simulated arm's budget.
- Each child evaluator uses the identical logistic structural learner. Freeze
  child weights and all zero-query target choices before opening target
  scoring labels. Report target candidate reachability and per-bank scores.

## Decision rule and limits

Primary endpoint: paired low-confidence minus source-order child accuracy on
the fresh target. Require positive gain on at least five of six banks and a
six-bank resampling 95% interval above zero. Also require low-confidence to
exceed the strongest other fixed acquisition control in aggregate before
naming it the best supported 7,000-label acquisition rule. The iterative arm
must beat its frozen low-confidence counterpart at equal labels to claim that
online improver updates help. These are separate claims.

Report candidate generation, public feature, verifier, and training costs.
This is a synthetic domain with finite-example correctness. The source and
target files are local; code-flow separation and predecision records are
auditable but do not provide independent host access control.
