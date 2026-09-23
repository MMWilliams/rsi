# Verified-frontier distillation: audited results

Run: `frontier-distillation-20260916-v11`. Engineering screen: **failed**. RSI remains unproved.

4 harvest controls, 3 training seeds, 2 rounds; common bootstrap and task-balanced anchor/cumulative replay. Final scores were deferred until decisions closed.

## Selected checkpoints

Means across configured training/evaluation seeds on the same final task bank.

| Condition | Initial pass@64 | Selected round 1 | Selected round 2 | Final pass@1 |
| --- | ---: | ---: | ---: | ---: |
| baseline_selected | 20.83% | 20.83% | 20.83% | 6.30% |
| corrected_selected | 20.83% | 20.83% | 20.83% | 6.30% |
| corrected_first_verified | 20.83% | 20.83% | 22.40% | 9.43% |
| corrected_frontier | 20.83% | 19.27% | 20.31% | 9.11% |

Unadapted base mean pass@64: 0.00%. Frozen bootstrap: 20.83%.

## Measurement scope

- Observed raw neural pass@k on this frozen final bank, averaged across the configured seeds.
- Task within checkpoint within training seed; the same tasks recur across arms and seeds.
- Each training seed also determines an evaluation seed; seed variation mixes training and generation randomness.
- Per-seed contrasts are descriptive; no confidence interval or population-level significance claim is made.
- The preregistered advancement screen is an engineering decision, not proof of RSI.
- Controls compare complete training pipelines; weight-level causes and transfer to other domains are not identified.
- Research, cybersecurity, social good and policy remain intended applications with separate outcome evaluations outstanding.

## Raw pass@k curves

Mean selected round-two checkpoints; every declared k is shown. These columns reuse the same samples and are not independent tests.

| Condition | pass@1 | pass@4 | pass@8 | pass@16 | pass@32 | pass@64 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| initial | 6.30% | 11.42% | 14.16% | 16.32% | 18.43% | 20.83% |
| baseline_selected | 6.30% | 11.42% | 14.16% | 16.32% | 18.43% | 20.83% |
| corrected_selected | 6.30% | 11.42% | 14.16% | 16.32% | 18.43% | 20.83% |
| corrected_first_verified | 9.43% | 12.77% | 14.56% | 16.58% | 19.18% | 22.40% |
| corrected_frontier | 9.11% | 12.83% | 14.59% | 16.14% | 17.90% | 20.31% |

## Preregistered screen

- positive_mean_primary_contrast: failed.
- positive_in_two_seeds: failed.
- above_frozen_bootstrap: failed.
- above_unadapted_base: passed.
- round_two_retains_round_one_mean: passed.

## Every checkpoint decision

Final effects compare the candidate with its actual parent; they did not influence admission.

| Change | Accepted | Admission gained / lost tasks | Final gained / lost tasks | Final pass@64 change | Admission reason |
| --- | --- | ---: | ---: | ---: | --- |
| s17_baseline_selected_round1 | False | 0 / 4 | 3 / 4 | -1.56% | previously_solved_validation_tasks_lost, large_k_validation_regression |
| s17_baseline_selected_round2 | False | 1 / 3 | 3 / 3 | +0.00% | previously_solved_validation_tasks_lost, large_k_validation_regression |
| s17_corrected_selected_round1 | False | 1 / 1 | 4 / 3 | +1.56% | previously_solved_validation_tasks_lost |
| s17_corrected_selected_round2 | False | 3 / 1 | 2 / 2 | +0.00% | previously_solved_validation_tasks_lost |
| s17_corrected_first_verified_round1 | False | 1 / 1 | 4 / 2 | +3.12% | previously_solved_validation_tasks_lost |
| s17_corrected_first_verified_round2 | False | 2 / 3 | 4 / 3 | +1.56% | previously_solved_validation_tasks_lost, large_k_validation_regression |
| s17_corrected_frontier_round1 | False | 0 / 2 | 3 / 3 | +0.00% | previously_solved_validation_tasks_lost, large_k_validation_regression |
| s17_corrected_frontier_round2 | False | 1 / 1 | 2 / 3 | -1.56% | previously_solved_validation_tasks_lost |
| s29_baseline_selected_round1 | False | 3 / 2 | 5 / 4 | +1.56% | previously_solved_validation_tasks_lost |
| s29_baseline_selected_round2 | False | 1 / 1 | 4 / 3 | +1.56% | previously_solved_validation_tasks_lost |
| s29_corrected_selected_round1 | False | 3 / 2 | 4 / 1 | +4.69% | previously_solved_validation_tasks_lost |
| s29_corrected_selected_round2 | False | 1 / 2 | 5 / 1 | +6.25% | previously_solved_validation_tasks_lost, large_k_validation_regression |
| s29_corrected_first_verified_round1 | False | 3 / 2 | 5 / 3 | +3.12% | previously_solved_validation_tasks_lost |
| s29_corrected_first_verified_round2 | True | 2 / 0 | 5 / 2 | +4.69% | coverage_retained_and_measured_gain |
| s29_corrected_frontier_round1 | False | 2 / 1 | 6 / 2 | +6.25% | previously_solved_validation_tasks_lost |
| s29_corrected_frontier_round2 | True | 2 / 0 | 3 / 1 | +3.12% | coverage_retained_and_measured_gain |
| s43_baseline_selected_round1 | False | 2 / 1 | 5 / 3 | +3.12% | previously_solved_validation_tasks_lost |
| s43_baseline_selected_round2 | False | 2 / 2 | 4 / 3 | +1.56% | previously_solved_validation_tasks_lost |
| s43_corrected_selected_round1 | False | 1 / 2 | 2 / 2 | +0.00% | previously_solved_validation_tasks_lost, large_k_validation_regression |
| s43_corrected_selected_round2 | False | 4 / 1 | 3 / 5 | -3.12% | previously_solved_validation_tasks_lost |
| s43_corrected_first_verified_round1 | True | 2 / 0 | 3 / 3 | +0.00% | coverage_retained_and_measured_gain |
| s43_corrected_first_verified_round2 | False | 1 / 1 | 2 / 4 | -3.12% | previously_solved_validation_tasks_lost |
| s43_corrected_frontier_round1 | True | 1 / 0 | 2 / 5 | -4.69% | coverage_retained_and_measured_gain |
| s43_corrected_frontier_round2 | False | 1 / 3 | 4 / 2 | +3.12% | previously_solved_validation_tasks_lost, large_k_validation_regression, pass1_validation_regression, no_measured_validation_gain |

## Controlled training-pipeline contrasts

- corrected_selected minus baseline_selected: +0.00% mean selected round-two pass@64; filter effect in this training pipeline. Seed deltas: {'17': 0.0, '29': 0.0, '43': 0.0}.
- corrected_first_verified minus corrected_selected: +1.56% mean selected round-two pass@64; additional solved training tasks. Seed deltas: {'17': 0.0, '29': 0.046875, '43': 0.0}.
- corrected_frontier minus corrected_first_verified: -2.08% mean selected round-two pass@64; multiple programs for the same training tasks. Seed deltas: {'17': 0.0, '29': -0.015625, '43': -0.046875}.

## Costs and limits

Runtime: 7990.83 seconds. Generated tokens: 2,619,318; supervised tokens: 108,059; optimizer steps: 1,152.

Full acquisition costs, exact-replay work, generated prompt/completion tokens, training draws and oracle checks are in results.json. Audit reexecution is additional verification work. Matched steps and examples do not match total compute or target-token counts.

Audit: 310 artifacts, 221,184 sample regradings, 1152 optimizer steps and 24 checkpoint decisions reconciled.

These are 3 training seeds sharing a bank and bootstrap, not independent task-bank replications. A finite gate can disagree with held-out outcomes. Syntactic variants need not be semantically distinct. Frozen harvest does not close the interleaved loop or prove improved improvers, inheritance, novel edit types or mission-domain benefit.

Per-change JSON links the exact pools, sampling evidence, checkpoint hashes and observed outcomes. Admission/final disagreement labels describe this sample; they do not establish a true error rate or authorize retrospective checkpoint selection.

Report-time independent audit: 150.33 wall seconds, 148.48 process CPU seconds, additional to the experiment ledger. The JSON receipt binds the report to the exact artifact manifest and audit output.
