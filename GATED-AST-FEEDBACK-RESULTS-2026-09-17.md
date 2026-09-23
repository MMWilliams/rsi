# AST specialist integration on fresh mixed banks

## Decision

**Do not promote the gated AST specialist as an improved seed evaluator.** On six new 48-task banks covering six synthetic mechanisms, widening the AST candidate sources raised total reachability from **229/288 to 245/288**, with paired gains of +3,+2,+3,+3,+2,+3 tasks per bank and an exact six-bank resampling 95% interval of **+14 to +18**. But the AST specialist selected **0/48** correct AST programs despite **26/48** reachable pools. The public-context gate therefore tied the parent on the same wide pools at **135/288**. A fixed prior temperature map scored **139/288**. The 288-task reconstruction audit passed.

The prior AST-only fresh test had produced 6/48 correct specialist selections. This second, independently seeded mixed-bank test found zero with the same model and cap-512 AST sources. That earlier scoped gain is real for its tested instances but did not replicate across the benchmark's mixed task-generation stream. The declared gate required at least five positive banks and a positive bank interval; all six paired gate differences were zero. The seed improver remains unproved.

## Frozen policies and results

The gate used only public input characters: codepoint block 0x800 selected the AST specialist; other blocks retained the parent temperature-0.25 ranker. The benchmark's mechanisms occupy distinct Unicode blocks, making this a simple synthetic routing cue. Candidate generation followed the previous family-to-source map at cap 128, while AST alone received V67/V73 cap 512. The simulator's host family tag selected candidate sources as in the earlier mixed-bank study; it was not given to evaluator models or the gate.

| Policy on 288 tasks | Correct |
| --- | ---: |
| Parent 0.25, cap-128 pools | 135 |
| Parent 0.25, AST widened | 135 |
| AST specialist globally, AST widened | 125 |
| Parent plus AST public-context gate | 135 |
| Prior fixed block-temperature map | **139** |
| Fixed map plus AST gate | **139** |

The specialist's global losses were concentrated in transformation (10→6) and self-edit (45→37); it gained two on novel operators and tied stack and mutation. Routing avoided those non-AST losses by construction, but it supplied no AST gain. AST reachability itself rose **10→26/48**, leaving 26 reachable tasks unsolved by every tested no-query ranker. Preparation generated **50,330** baseline candidate entries and **24,786** entries in the separately saved wide AST pools. Wall time was **187 seconds**, with **893 summed source-generation seconds** across workers. The specialist had already consumed **23,686** additional source candidate labels beyond the parent's 31,500; inference used zero oracle output queries.

The run froze seeds 902294–902299, tasks, pools, model hashes and all choices before final labels were opened. The audit regenerated all 288 tasks and pools, replayed 576 base/wide model-choice sets, rechecked **118,228** candidate outcomes and matched all saved results. It passed. Finite hidden-example correctness and repeated rules still limit what this benchmark establishes.

## Failure diagnosis and next test

On the earlier AST-only bank, the specialist put a correct program in its top ten on **18 of 26** reachable tasks and selected six. On this mixed bank, it put one in its top ten on **11 of 26** reachable tasks and selected none. The candidate pool was not empty of solutions; the evaluator's ranking signal shifted. In the first bank all six successes were on `affine_fold`; the second bank had 11 reachable `affine_fold` tasks and none selected. This is a post hoc diagnosis, not a new transfer claim. Details are in `analysis/ast-feedback-failure-diagnostic.json`.

The next evaluator work should target ranking reliability on widened pools and use the inspected banks only for development. Candidate-class aggregation or cost-matched active output queries are plausible edit types; each must beat its fixed controls on new banks. For the improver, preserve the strong parent and fixed-map controls, require protected admission to reject updates like this one, then test whether inherited edit-effect feedback makes a later parent produce a better child improver on a second untouched bank. No global or gated AST specialist is promoted from this study.

Protocol: `EXPERIMENT-gated-ast-feedback.md`. Runner and audit: `gated_ast_feedback.py`, `audit_gated_ast_feedback.py`. Frozen data: `runs/gated-ast-feedback-20260917/`. Diagnostic: `ast_failure_diagnostic.py`, `analysis/ast-feedback-failure-diagnostic.json`.
