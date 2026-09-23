# Verified-frontier training: related work and measurement choices

Checked primary sources on 2026-09-16. This is a targeted update, not a novelty
certification or an implementation reproduction.

- [ReST-EM, final abstract](https://arxiv.org/abs/2312.06585): iterative generation,
  binary filtering and fine-tuning already constitute established prior art.
  Our search-produced DSL targets and inherited-improver question differ; merely
  repeating verified distillation is not a novel RSI result.
- [Where does output diversity collapse in post-training?](https://arxiv.org/abs/2604.16027),
  April 17 abstract inspected: comparisons across Olmo 3 lineages associate
  diversity changes with training-data composition and distinguish removal of
  incorrect outputs from narrowing among correct outputs. We therefore record
  verified multiplicity and task coverage separately. This is an inference for
  experiment design, not evidence that extra DSL programs will prevent collapse.
- [Rethinking On-Policy Distillation II](https://arxiv.org/html/2609.04172v1),
  September primary paper revisited; earlier section-level scope is recorded in
  `research-retention-2026-09-16.md`. Its on-policy teacher/student setting differs
  from our hard-target search distillation. We keep task-count, target-multiplicity
  and optimizer interventions separately interpretable rather than adopting an
  on-policy label for supervised replay.

V9 uses first-selected, first-verified and all-verified corrected-search targets,
plus an original-filter control. Uniform task-then-program sampling prevents a
task with many syntactic variants from automatically receiving more examples.
A fixed anchor fraction and cumulative harvest are common retention conditions;
their efficacy remains unproved. A larger admission bank is also a testable
choice, not a proof against regression. Frozen, unadapted-base and per-round
comparisons protect the distinction between a better training artifact and a
better recursive improver. Protocol: `EXPERIMENT-v9-frontier-distillation.md`.
