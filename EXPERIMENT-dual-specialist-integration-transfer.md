# Frozen dual-specialist evaluator and improver transfer (2026-09-18)

## Question and target

Can the validated familiar and shifted top-100 evaluators be combined into a better zero-query general seed on untouched mixed AST tasks? Does adding verified paired-action feedback make the later controller a better improver than its earlier checkpoint, scrambled feedback and duplicate history?

Generate 24 new eight-task mixed banks, seeds 903900–903923, four familiar and four shifted tasks per bank, one visible and 23 hidden examples. Use identical V67/V73 widened pools and old/E0 records for every policy. The primary outcome is final correctness of the first candidate with **zero external output calls**. The existing pipeline's predicted outputs are recorded as internal compute, and no probe answer enters a policy choice.

## Frozen actions and controllers

Fixed actions are familiar early top-100 and shifted AB top-100; E0 is a general fallback. A static public confidence rule chooses shifted AB when its top-candidate correctness probability exceeds the familiar model's top probability, otherwise familiar. The prior frozen public-feature route is another fixed control. An unavailable per-task best-of-two is a ceiling.

The **improver** fits a ridge model to verified shifted-minus-familiar final-correctness effects using public visible-pair and candidate statistics. Early receives 192 prior mixed tasks; later receives those plus 192 more audited mixed tasks. Scrambled-later permutes only the added effects within each eight-task bank; duplicate-history adds 192 resampled early task rows, balanced by task type, without new information. All use the same zero predicted-effect threshold and candidate pools. A separate later nonlinear effect regressor is exploratory. Target features exclude family, generator, reference, seed, task ID, hidden examples and probe answer. Task type is used only to balance a control and report subgroups.

## Frozen gates

The static dual-specialist **integration** gate requires the confidence rule to beat the stronger of fixed familiar and fixed shifted by at least 12/192, improve at least 12 of 24 paired banks, have a paired bank interval above zero, and not fall below either specialist by more than eight tasks on that specialist's own task subgroup. This can support a scoped combined evaluator, not an improving controller.

The **improver-growth** gate requires later ridge to exceed early ridge, scrambled-later, duplicate-history and the fixed confidence rule by at least five tasks each, improve at least eight banks over early, and have strictly positive paired bank intervals against all four. Report every criterion. More source records or a better fixed combination alone cannot pass this gate.

Freeze protocol, code, models, target public artifacts and choices before scoring hidden outputs. Rebuild source outcomes, model predictions on evaluated rows, target tasks, pools, predictions, choices and all candidate final labels in a separate audit. Model file hashes must remain fixed; if retrained model-object hashes differ, exact probabilities/predictions on every evaluated source and target row plus full target replay are required and the qualification is recorded. A failed audit invalidates the result. Report source acquisition, candidate scoring and prediction costs separately from output calls.
