# Confirmation metrics addendum

Recorded after source discovery and before confirmation labels or decisions are opened. The primary endpoints and seed-selection rule remain those in `EXPERIMENT-seed-confirmation.md`.

Secondary learning-efficiency metric: mean held-out utility across the five declared checkpoints, including round zero. Each round buys the same four-task allowance; report actual candidate oracle queries separately rather than calling this a matched-CPU metric. Compare final utility and the learning curve, so a faster useful update can be distinguished from a better endpoint. Do not select a new final winner by choosing whichever metric looks favorable.

Retain the initial lexical evaluator as a strong no-update control alongside the initial selected driver and frozen ranker. Its source admission score was 18/18; therefore the source-selected controller has not established superiority over all initial components.
