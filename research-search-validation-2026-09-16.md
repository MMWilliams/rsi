# Search-policy validation and current related work

Primary-source check on 2026-09-16: [Dream-RSI v1](https://arxiv.org/html/2609.14858v1),
dated September 14. Inspected sections 2–4, including the replay interface,
objective, selection rule and controlled baseline; repository not audited.
The system updates exploration-policy code through a fixed LLM development
agent while keeping discovery models and evaluator fixed. Recorded trees support
offline branch allocation and stopping-policy evaluation. Replay reveals existing
children in recorded order; it does not generate outcomes on unobserved branches.
The selected policy improves the score on the fixed replay histories by
construction; this alone does not guarantee prospective improvement. Experiments
compare adaptive with fixed exploration and emphasize discovery-agent-call costs.

Implications for our design (inferences): archive reuse and learned exploration
are established related work, not sufficient novelty claims. Our exact candidate
reproduction and their counterfactual traversal are different uses of replay.
Neither permits inventing unseen outcomes. Fresh tasks, full acquisition and
meta-optimization costs, and common-ancestor improver tests remain necessary for
our claim. The new v8 study tests a human-directed filter correction, so it must
not be presented as a reproduction or extension demonstrating Dream-RSI.

The prospective protocol is `EXPERIMENT-v8-search-validation.md`. Its budget
curves keep primitive work, search expansions and time separate. Reusing the
two component outputs to construct a fixed mixture still incurs both inference
costs. These choices address our observed regressions and cost increase; they
are not empirical consequences of the cited paper.
