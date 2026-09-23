# Familiar AST candidate-feedback evaluator: fresh transfer

## Decision

The familiar-specific top-100 evaluator passed its prospectively frozen **component** gate on 24 untouched familiar AST banks (192 tasks). Its early checkpoint selected **108** final-correct first programs with zero external output calls, versus E0 at **38**, pooled at **49**, and shifted AB at **10**. It improved 23 of 24 banks over E0 and 23 over pooled, with no losing bank; the paired gain intervals were **+58 to +82** and **+48 to +70**. The old top 100 contained a correct program for 112 tasks, so the early checkpoint chose a correct program on 108 of 112 top-100-reachable tasks.

The later checkpoint selected **110**, but its +2 over early occurred on only two banks and its paired interval **0 to +5**. It beat scrambled added labels by four and duplicate history by two. The distinct incremental evaluator-growth gate failed. Retain the early checkpoint as the parsimonious familiar specialist; the later model's two extra tasks do not justify claiming an improving feedback process.

The source early checkpoint used 19,152 verified candidate labels from 192 familiar tasks; later used 28,722 labels from 288 tasks. All policies saw the same V67/V73 widened candidate pools and zero external output calls. Each top-100 model scored 18,954 target candidates; public preparation computed 745,504 predicted probe-output cells, which are recorded as internal computation cost. The frozen protocol is `EXPERIMENT-familiar-ast-zero-query-transfer.md`. Full results and reconstruction status are in `runs/familiar-ast-zero-query-transfer-20260918/`.

The first audit command stopped because retrained model-object hashes differed. A frozen [audit addendum](AUDIT-ADDENDUM-familiar-ast-zero-query-2026-09-18.md) required exact functional equivalence instead. That replacement audit **passed**: all four retrained models produced exactly the same probabilities as the frozen models on **28,722 source** and **18,954 target** candidate rows per model, and it rebuilt all 192 tasks, 745,504 predicted cells, 93,188 final candidate labels and frozen choices. The saved `audit.json` records the object-hash qualification. The result is supported for the evaluated rows, without claiming byte-identical models or behavior on untested features.

## Result table

| First-choice evaluator | Correct / 192 |
|---|---:|
| E0 | 38 |
| Shifted AB | 10 |
| Pooled familiar-plus-shifted | 49 |
| Familiar early top-100 | **108** |
| Familiar later top-100 | 110 |
| Later with added labels scrambled | 106 |
| Early history duplicated to match rows | 108 |

The full pool contained a correct program for 118/192 tasks; the top 100 reached 112. This component nearly saturates its available shortlist on this synthetic familiar mechanism. Further candidate-ranker training has little headroom here unless candidate generation or shortlist recall changes.

## Scope and next integration

The shifted AB checkpoint remains the supported shifted-task specialist, while the new early checkpoint is the strongest tested familiar-task first-choice evaluator. Applying either globally harms the other mechanism. The next protected test must route **between these two strong actions** using public task evidence and verified per-action effects, with an earlier/later improver comparison, scrambled feedback, duplicate history and charged candidate-scoring cost. The opened panels are useful for screen design only. Neither this component result nor its failed incremental checkpoint proves a self-improving improver or mission-domain transfer.
