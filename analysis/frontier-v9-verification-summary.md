# Verified-frontier distillation: audited results

**Implementation verification fixture only. Its tiny task bank and one-step
updates are not research evidence or a replication of the v9 study.**

Run: `frontier-v9-verification-fixture-v2`. Engineering screen: **failed**. RSI remains unproved.

4 harvest controls, 1 training seeds, 2 rounds; common bootstrap and task-balanced anchor/cumulative replay. Final scores were deferred until decisions closed.

## Selected checkpoints

Means across training seeds on the same final task bank.

| Condition | Initial pass@64 | Selected round 1 | Selected round 2 | Final pass@1 |
| --- | ---: | ---: | ---: | ---: |
| baseline_selected | 0.00% | 0.00% | 0.00% | 0.00% |
| corrected_selected | 0.00% | 0.00% | 0.00% | 0.00% |
| corrected_first_verified | 0.00% | 0.00% | 0.00% | 0.00% |
| corrected_frontier | 0.00% | 0.00% | 0.00% | 0.00% |

Unadapted base mean pass@64: 0.00%. Frozen bootstrap: 0.00%.

## Preregistered screen

- positive_mean_primary_contrast: failed.
- positive_in_two_seeds: failed.
- above_frozen_bootstrap: failed.
- above_unadapted_base: failed.
- round_two_retains_round_one_mean: passed.

## Every checkpoint decision

Final effects compare the candidate with its actual parent; they did not influence admission.

| Change | Accepted | Admission gained / lost tasks | Final gained / lost tasks | Final pass@64 change | Admission reason |
| --- | --- | ---: | ---: | ---: | --- |
| s991_baseline_selected_round1 | False | 0 / 0 | 0 / 0 | +0.00% | no_measured_validation_gain |
| s991_baseline_selected_round2 | False | 0 / 0 | 0 / 0 | +0.00% | no_measured_validation_gain |
| s991_corrected_selected_round1 | False | 0 / 0 | 0 / 0 | +0.00% | no_measured_validation_gain |
| s991_corrected_selected_round2 | False | 0 / 0 | 0 / 0 | +0.00% | no_measured_validation_gain |
| s991_corrected_first_verified_round1 | False | 0 / 0 | 0 / 0 | +0.00% | no_measured_validation_gain |
| s991_corrected_first_verified_round2 | False | 0 / 0 | 0 / 0 | +0.00% | no_measured_validation_gain |
| s991_corrected_frontier_round1 | False | 0 / 0 | 0 / 0 | +0.00% | no_measured_validation_gain |
| s991_corrected_frontier_round2 | False | 0 / 0 | 0 / 0 | +0.00% | no_measured_validation_gain |

## Causal contrasts

- corrected_selected minus baseline_selected: +0.00% mean selected round-two pass@64; filter effect in this training pipeline. Seed deltas: {'991': 0.0}.
- corrected_first_verified minus corrected_selected: +0.00% mean selected round-two pass@64; additional solved training tasks. Seed deltas: {'991': 0.0}.
- corrected_frontier minus corrected_first_verified: +0.00% mean selected round-two pass@64; multiple programs for the same training tasks. Seed deltas: {'991': 0.0}.

## Costs and limits

Runtime: 57.39 seconds. Generated tokens: 13,299; supervised tokens: 647; optimizer steps: 8.

Full acquisition costs, exact-replay work, generated prompt/completion tokens, training draws and oracle checks are in results.json. Audit reexecution is additional verification work. Matched steps and examples do not match total compute or target-token counts.

Audit: 136 artifacts, 1,664 sample regradings, 8 optimizer steps and 8 checkpoint decisions reconciled.

These are 1 training seeds sharing a bank and bootstrap, not independent task-bank replications. A finite gate can disagree with held-out outcomes. Syntactic variants need not be semantically distinct. Frozen harvest does not close the interleaved loop or prove improved improvers, inheritance, novel edit types or mission-domain benefit.

Per-change JSON links the exact pools, sampling evidence, checkpoint hashes and observed outcomes. Admission/final disagreement labels describe this sample; they do not establish a true error rate or authorize retrospective checkpoint selection.
