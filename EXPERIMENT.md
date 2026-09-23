# RSI pilot protocol — declared before the first run

This implements the system-level proposal authorized on 16 September 2026. It is an engineering pilot and an empirical comparison, not evidence of optimality or a claim that RSI has been achieved. H1 becomes a later optional operator study.

The trusted host owns task generation, hidden examples, final scoring, journals, and the acceptance decision. A worker receives visible examples and bounded declarative search configurations only. Model-created edit operators are expressions interpreted by a small allowlisted evaluator; the model receives no shell or filesystem tools. Arbitrary self-modifying Python is deliberately outside this prototype's threat model. Same-user hostile native code is not sandboxed by this design.

The domain is the published trapdoor DSL, pinned at commit `dd78141b423b661571f873d55f157b4e8a01e615`. A separately implemented AST interpreter cross-checks the upstream interpreter and provides authoritative scoring. Verification is exact on the tested strings; finite examples do not prove universal program equivalence.

## Measurements

- Search: selected-solution accuracy on a fresh final bank at a fixed expansion budget, with primitive enumeration, expansion, replay, oracle, and wall time costs reported separately. Final tasks are never used to select edits.
- Improver: generation 0/3/6 effect tables restart from the identical search configuration and operator catalog; after the same edit opportunities, compare final task accuracy. Descendant statistics are observational evidence, not causal proof.
- Inheritance: intact/empty/scrambled effect tables; all restart with identical executable rules, macros, and search configuration. Scrambling permutes entire statistic records across operator identities. Common tasks and repeated seeds are paired.
- Neural: raw model pass@1/4/8/16/32/64 without amplifier assistance before and after verified LoRA distillation. Compare search-distillation with verified self-training at the same optimizer steps. Report the different synthesis and oracle costs; this pilot does not establish equal total compute.
- Controls: frozen search, random edits through identical gates, frozen uniform edit selection, and table-only inheritance. A SOAR-inspired fixed search plus distillation arm is labeled as an adaptation, not a reproduction of SOAR. No paid external model is required for the pilot.

## Gates and stopping rules

Every candidate must validate against a bounded schema, produce a bit-identical search trace when replayed with recorded inputs and seed, agree with independent execution sensors, and improve development accuracy without regressing on that generation's admission tasks. Replay re-executes the worker; cached LLM proposals are part of its input. It does not claim GPU sampling is bit-exact across hardware.

Development and admission slices rotate by generation. Adaptive feedback makes these validation data, not a final holdout. Train/development/admission/final/transfer programs are disjoint by canonical program and by a template signature that removes literal string contents. A new final bank is generated; published banks are retained only as reference artifacts.

Run the preset's fixed six generations and paired seeds. Do not extend the run or change acceptance thresholds in response to final outcomes. The first GPU run uses Qwen3-0.6B and one training seed to test the complete path; it is not a replication of Qwen3-4B and cannot establish robust neural gains. Record all failed proposals and empty-data training skips. No favorable effect is required for completion.

Success for the engineering pilot means intact oracle boundaries under the implemented threat model, deterministic replay, verified training provenance, and complete comparative measurements. Scientific success requires reliable positive effects in separately preregistered, powered runs. If the prototype fails or a correctness bug is found, retain the failed run and label the corrected rerun.
