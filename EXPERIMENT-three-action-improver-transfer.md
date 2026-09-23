# Frozen three-action evaluator/improver transfer (2026-09-18)

## Question

Does a controller trained on verified correctness for three evaluator actions—E0, shifted AB and pooled candidate ranking—integrate them better than any fixed action on untouched mixed tasks? Does adding verified mixed-task feedback make the later controller a better improver than its earlier parent, scrambled feedback and duplicate history?

## Frozen bank and policies

Generate 24 new eight-task mixed banks, seeds 903700–903723, each with four familiar and four shifted AST tasks, one visible and 23 hidden examples. Use the same V67/V73 widened candidate pool and old/E0 ranking pipeline for every policy. The primary outcome is final correctness of the first choice with **zero external output calls**. Predicted probe outputs computed by the existing pipeline are charged as internal work; no probe answer enters the choices.

The three-action controller fits one candidate-correctness classifier per action and selects the action with the highest predicted probability, stable ties in E0/AB/pooled order. Its only target inputs are the visible pair and public candidate statistics defined in `zero_query_router_development.public_row`; family, reference, task ID, seed, hidden examples and probe answer are excluded. Train early on 288 prior tasks and later on those plus 192 verified mixed tasks. Controls add scrambled mixed action-outcome tuples within bank or 192 balanced duplicate source rows. Fixed E0, AB, pooled and the previously frozen two-action public-feature route share the target pools. The unavailable per-task best of the three actions is reported as a ceiling.

## Decision gates

Integration passes if the later three-action controller beats always AB by at least 8/192, improves at least eight of 24 paired banks, has a paired bank interval above zero, scores at least E0 minus two on familiar tasks, and scores at least AB minus three on shifted tasks. Report every criterion and the matched candidate-score and source-label acquisition costs.

Incremental improver growth passes only if the later controller exceeds **each** of early, scrambled and duplicate-history controllers by at least five tasks, improves at least eight banks over early, and has positive paired bank intervals against all three. A passed integration gate alone does not imply improver growth.

Freeze source models, protocol, code, public bank, candidate pools and choices before scoring hidden target outputs. Independently rebuild tasks, pools, predictions, model choices and all final candidate labels. Any audit failure invalidates the results. This synthetic test does not establish open-ended recursion, equal total compute or transfer to mission domains.
