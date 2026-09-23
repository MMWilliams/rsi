# Retention and causal logging: targeted research update

Checked 2026-09-16. This is a targeted primary-source check, not an exhaustive survey or novelty certification.

| Source and inspected scope | Relevant finding | Decision for this project | Limit |
| --- | --- | --- | --- |
| [Gerstgrasser et al., 2024, v2](https://arxiv.org/abs/2404.01413), abstract | Accumulating original and synthetic data avoided collapse in their experiments. | Test cumulative verified replay against replacement. | Their real/synthetic-data setting differs from our exact-verifier DSL and LoRA training; no guarantee here. |
| [Nicolicioiu et al., June 24 2026](https://arxiv.org/abs/2606.26091), abstract | Demonstration-conditioned on-policy self-distillation can concentrate modes despite strong average performance. | Measure large-k coverage and diversity alongside pass@1. | Our hard-target supervised loss is different; their mechanism is not established in our run. |
| [Yang et al., August 30 2026](https://arxiv.org/html/2608.29846v1), introduction and sections 2-3 | Sampled-token OPD updates can reduce entropy; their method selectively shrinks entropy-contracting advantages. | Keep entropy-aware/on-policy objectives as later controlled interventions. | We do not implement IDA-OPD by renaming supervised replay. Its teacher probabilities and rollout objective are absent here. |
| [Rethinking OPD II, September 2026](https://arxiv.org/html/2609.04172v1), sections 4.2 and appendix B.2 | Controlled response/query-diversity experiments connect state coverage to performance; small query counts can still work. | Separate dataset size, diversity, and update-policy effects. | Few training examples alone do not prove the cause of our regression. |

The immediate v3 change is intentionally interpretable: retain prior verified trajectories, compare with a replacement control, and separately test checkpoint promotion. Parent regularization and contextual effect tables remain open. The RSI success requirements are unchanged: compounding large-k coverage, stronger improvers from the same ancestor, causal inheritance, and matched-compute controls.

Logging design: hash and archive raw evidence, source, config and checkpoints; record proposals before training and decisions before final scoring; retain rejected candidates; log exact optimizer draw indices and losses; separate measured changes from mechanistic explanations; preserve failed runs. Hash chains detect corruption relative to a trusted head but are not authenticated against a writer who can replace the entire archive. Saved RNG seeds do not by themselves guarantee bit-identical GPU training across machines.
