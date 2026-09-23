# Ten-version integration pilot

Two fresh mixed-family semantic banks and two disjoint DSL banks completed under
`EXPERIMENT-stitch-ten.md`. The first attempted archive
`runs/stitch-ten-pilot-20260917` was rejected by its source-integrity gate when
`rsi/evolving_domain.py` changed during the run. It is retained as failed and
excluded. The completed archives are `runs/stitch-ten-pilot-20260917b` and
`runs/stitch-ten-pilot-20260917c`.

## Independent audit

Both completed runs passed independent replay: 95 sealed artifacts, 36
regenerated semantic tasks, 324 candidate-generation calls reexecuted across
nine sources, and 24 DSL searches reexecuted per run. The auditor recomputed
the source priority, admission decision, every final program grade, and the
disjoint DSL bank. Programs and candidate envelopes contained visible examples
and task IDs only during proposal generation; hidden examples were used only
by the host grader.

## Held-out comparison

| Fresh bank | Semantic router | Best native semantic arm | Random-priority router | DSL V8 | Original DSL search |
| --- | ---: | ---: | ---: | ---: | ---: |
| 203117 / DSL 203118 | 10/12 | 8/12 (V73, V75, V80) | 3/12 | 9/12 | 5/12 |
| 203119 / DSL 203120 | 10/12 | 7/12 (V73, V75, V80) | 6/12 | 8/12 | 8/12 |

The source priority was selected using development and admission only. In the
first bank, V67 solved both transform tasks that V73 missed. In the second,
V67 and V73 covered different tasks, including stack tasks supplied by V73.
The other seven semantic sources did not add a unique final solve in either
bank. Removing one source at a time left the first score at 10/12; removing
V67 reduced the second score to 9/12. Several sources returned identical
programs, so source provenance alone is not a causal ablation of the underlying
representation.

An exploratory post-run replay of the archived candidate pools found that a
V67+V73-only selector also scored 10/12 on both banks, and adding V72 did not
change either score. This subset was chosen after seeing the final outcomes;
it is a hypothesis for a new prospective run, not a confirmatory comparison.

## Cost and limits

Each semantic source received 36 task calls and a cap of four archived
candidates per call. Across the nine sources, generation took about 177 and
162 seconds and produced 620 and 612 archived candidates. The router used all
these generated pools, while a native arm used only its own. Actual primitive
executions for semantic candidate generation were not instrumented; these are
not equal-compute superiority results. V8 ran only in the DSL lane and did
not exchange executable programs with the semantic arms. Neither pilot
jointly evolved V67's scoring genome, V72's mutation policy or V73's grammar;
the stitched component is a source-priority router over their proposal
generators. The two 12-task final banks share the same authored six-family
mixture, with two tasks per family, and are not a broad domain replication.

The observed complementarity justifies a narrower V67+V73 router with matched
candidate-generation cost, a direct-search control and at least six fresh
groups. It does not establish that all ten components contribute, that the
system improves its own improvement process, or that it has value in research,
cybersecurity, social good or policy tasks.
