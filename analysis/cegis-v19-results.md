# V19 neural-seeded CEGIS result

V19 changed the search substrate from progressive widening to a visible-only
counterexample-guided shortest-path solver. The solver treats each visible
output prefix as a state, retains atoms that are empty on some visible
examples, and admits neural-proposed DSL atoms or contiguous fragments only
after visible execution and substring checks.

Two fresh 24-task banks were run with the same bounded DSL, visible/hidden
split, search budget, neural model revision, and one verified distillation
round.

| Condition | Bank A | Bank B | Pooled |
| --- | ---: | ---: | ---: |
| Progressive baseline | 19/24 | 15/24 | 34/48 |
| Progressive partial-empty control | 18/24 | 18/24 | 36/48 |
| Exact visible-only CEGIS, no neural proposals | 20/24 | 19/24 | 39/48 |
| Neural-seeded ranked CEGIS, pre-update | 21/24 | 19/24 | 40/48 |
| Neural-seeded ranked CEGIS, post-update | 21/24 | 19/24 | 40/48 |

The algorithmic result replicated: exact CEGIS exceeded the ordinary baseline
by 1 task on Bank A and 4 tasks on Bank B. The partial-empty control did not
explain the full gain; exact state search recovered visibly reachable programs
that the progressive queue missed. On Bank A, a neural proposal also supplied
a visible-compatible multi-character constant (`'- '`), adding one task over
the no-proposal CEGIS result. That neural expansion did not replicate on Bank
B, where ranked CEGIS tied exact CEGIS.

The learning result was null at this scale. Verified CEGIS distillation left
ranked final coverage unchanged within both banks. Raw neural pass@16 was only
5/24 and 4/24 before the updates, while CEGIS repair reached 21/24 and 19/24;
the verifier/search substrate, not the model alone, supplied most of the
measured capability.

Both archives passed independent replay audits. Each regraded 888 selected or
sampled programs; Bank A rechecked 18 verified rows and Bank B rechecked 19.
The audits do not rerun neural optimization and do not authenticate the host.

## Limitation and next test

This remains bounded synthesis, not RSI. The state space is limited to four
atoms, finite visible examples, a fixed interpreter, and a fixed model. The
next discriminating experiment should learn reusable typed transitions across
training tasks, then test whether those transitions expand CEGIS coverage on
new banks without hidden-example selection.
