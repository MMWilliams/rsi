# Retention experiment v3: declared before evaluation

2026-09-16. Goal: repair and causally investigate the distillation bottleneck before resuming the full recursive loop. This is an ablation on frozen verified trajectories, not evidence that an improver has improved.

## Intervention and controls

All three arms load the exact same saved v2 bootstrap adapter. Use v2 search-round trajectories as fixed inputs, independently reverified now. Fresh: train on the current round only. Replay: train uniformly over the deduplicated union of bootstrap and all available rounds. Replay + gate: identical replay training, but reject updates that fail validation. The first comparison isolates cumulative retention at matched optimizer steps. The second isolates promotion policy, including its effect on the next round's parent. No parent KL, learning-rate change, or extra search is introduced in this experiment.

Two rounds, 48 AdamW steps each, batch 8, learning rate 0.0002, seed 17. Task/program pairs are canonically deduplicated; sampling is uniform over pairs, with replacement. No claim of semantic balance. The bootstrap checkpoint and frozen harvest are shared historical costs and reported as such, not free recursive gains. All arms receive the same nominal validation and final sample budgets. Generated tokens, training tokens, steps, and wall time are logged separately; total compute is not matched.

## Data and promotion

Generate new task banks with seed 9162603 and exclude literal-scrubbed reference templates from every previous local bank, including failed runs. Each round gets 12 fresh validation tasks, shared across arms but never reused for the next round. Final evaluation has 24 separate tasks. Template separation is syntactic, not proof of semantic independence. Hidden examples and references never enter model prompts or training targets for validation/final tasks.

Sample 64 programs per task with the v2 decoder. Evaluate parent and candidate using the same round-specific RNG seed. Gate requirements: no previously solved validation task is lost at n=64; aggregate pass@64 and pass@1 do not decrease; at least one increases strictly. A tie is rejected. This is an observed-sample decision, not a statistical guarantee. We deliberately do not optimize syntactic diversity as fitness. Small validation sets can accept regressions elsewhere or reject useful changes.

Keep rejected candidates and save selected adapters separately. Verify rollback with exact tensor hashes. Archive candidate final generations while withholding their scores until all six decisions are resolved. Report initial, every candidate, and each arm's selected model so a gate cannot hide poor proposals. No tuning or retries based on final scores.

## Outcomes and explanation

Primary diagnostics: paired replay-minus-fresh final pass@64 and gated-minus-ungated replay final pass@64. Also report pass@1/4/8/16/32/64, each transition's lost/gained task IDs, parseable syntactic diversity, visible-behavior signatures, training losses, sampled row indices, gradient norms, and complete costs. Bootstrap task intervals are descriptive; one training seed cannot establish robust superiority. Syntax/visible behavior are proxies, not universal program equivalence or model entropy.

Every change record must include its hypothesis, intervention, parent/candidate/selected tensor hashes, training-pool hash, seed, gate measurements, acceptance reason, rollback verification, raw-output references, and measured outcome. Explanations distinguish observations from causal hypotheses. Fresh versus replay can support a causal statement about this intervention under this fixed setup; the mechanism of forgetting versus optimization remains unresolved.

Run once to completion. Abort on nonfinite loss/gradient, unverified training row, changed source, invalid source manifest, or rollback mismatch; preserve a terminal failure record. Audit raw scores with the published interpreter and independently recompute pass@k and gate decisions. Further replication and re-integration are separate predeclared experiments.
