# Adjacent evaluator-improvement evidence, 17 September 2026

This note updates the gap assessment while the prospective same-base improver transfer test runs. Both sources below are recent author preprints, so their reported outcomes should be treated as claims to examine rather than established independent replications.

## RecurSE

[RecurSE: Bounded Recursive Self-Evaluation for LLM Rubric Judges](https://arxiv.org/abs/2608.24231) (25 August 2026) trains a judge while a synchronized policy copy checks the judge's reasoning. The checker emits a scalar reward through a distinct interface to prevent a direct verdict-token shortcut. A small human-verified validation set monitors both judge accuracy and checker ranking fidelity for early stopping. The authors report held-out gains across several model sizes and domains, and report that synchronized judge/checker updates outperform frozen checkers in their ablations.

**Consequence for RSI:** improving an evaluator through feedback is already demonstrated as a bounded research direction in a different setting, at least according to this preprint. Our synthetic program evaluator cannot claim novelty merely for improving a judge. The testable gap is whether evaluator improvements create a **better transferred improver**, under equal resource budgets and external outcome checks, over multiple generations. RecurSE's co-evolution and two-part validity monitor also motivate checking admitted accuracy and the quality of predicted edit effects separately. Our current gate checks admission correctness and probability error; it has produced held-out regressions.

## Self-evaluation bias in long-running loops

[When Do Agent Loops Mistake Stagnation for Progress?](https://arxiv.org/abs/2607.25152) (27 July 2026) compares evaluator information channels in a controlled agent loop. The authors report that 56% of 54 cycles had zero or negative externally measured change despite improvement claims, and that an in-band judge accepted real-world regressions. They emphasize grounding the gate in outcomes beyond the agent's transcript.

**Consequence for RSI:** accepted edits and a lower internal prediction error are process measurements; the research endpoint remains externally measured effect on sealed tasks. This distinction already matters in our v2 results, where several accepted tie promotions reduced final correctness.

These papers do not establish that our architecture is optimal or that their findings transfer to exact program synthesis. The current six-episode transfer experiment tests that narrower question with frozen controller checkpoints and task-execution labels.
