# Four-slot AST search, replay ranker, and output sensor

## Decision

**Do not promote the learned AST width improver or the fixed low-gap selector yet.** On twelve untouched 48-task mixed banks, the later feedback-updated child selected **319/576** correct programs, versus **323/576** for the initial child under the same four AST expansion slots and 96 true output calls. It was worse in four paired banks, better in none; the exact bank-bootstrap 95% interval for later minus initial was **-7 to -1**. The admission gate had already rejected later-parent deployment. The protected policy used the fixed low-gap rule and selected 323.

| Policy on the same 576 tasks | AST width slots | True output calls | Correct |
| --- | ---: | ---: | ---: |
| Base pools, no query | 0 | 0 | 306 |
| Wide AST pools, no query | 96 | 0 | 302 |
| Base pools, one query per AST task | 0 | 96 | 315 |
| Deterministic random four | 48 | 96 | 319 |
| Fixed low-gap four | 48 | 96 | **323** |
| Fixed high-entropy four | 48 | 96 | 318 |
| Initial learned child | 48 | 96 | **323** |
| Later learned child | 48 | 96 | 319 |
| Scrambled-history child | 48 | 96 | 320 |
| Duplicated-history child | 48 | 96 | 322 |
| Full wide AST pool, one query per AST task | 96 | 96 | 325 |

Low-gap improved by four over random four, but only five of twelve paired banks favored it; one bank lost, and its paired interval was **-3 to +10**. It did not pass the declared fixed-component gate. Full width gained two choices over low-gap while using twice the width slots, so it is a useful cost reference rather than a matched-budget winner.

## What this isolates

Each mixed bank contains eight AST tasks. A four-slot policy chose which four to expand using **only public features of the base pools**. The selected pool was ranked by the frozen replay AST evaluator. Every AST task then received one exact external output query, so every active policy spent eight calls per bank. Non-AST tasks used the same frozen public-context evaluator with no query. This isolates the search-width choice inside a fixed ranker/sensor package; it does not replace the previously stronger cross-family query allocator that can spend calls on non-AST tasks.

The candidate budget was four selected AST expansions per bank. Due to duplicate candidate programs, effective added entries varied: the fixed low-gap policy selected **16,746** extra candidate entries across transfer, versus **17,462** for random four and **34,116** for full width. The research harness generated all potential wide pools so every policy could be compared on identical tasks. Those shadow-generation costs were paid experimentally; the selected-entry counts describe deployment work and are **not** measured savings in this offline run. Candidate generation/inference cost and historical feedback are separate from matched true-output calls.

The initial ridge-10 parent learned from 144 opened AST effects; the later parent inherited 96 more. Both received the same 48 new admission effects. Observing both base and wide queried outcomes on those admission tasks required **64 distinct true probe outputs** across 48 AST tasks, plus final candidate labels. The parents tied at 153/288 on admission, two above random four, but that edge occurred in only one of six banks. The protected gate rejected later deployment under its four-positive-bank rule. On transfer, the later child scored 165 versus initial 168 on panel A and 154 versus 155 on panel B. More inherited feedback and common new feedback did not improve this width selector.

The fixed component has a coherent causal role even though its learned selector failed. Base-pool candidate reachability was **473/576** and full-width reachability **500/576**. Widening without an output query reduced top-choice correctness from 306 to 302, while widening plus the replay ranker and sensor raised the full-width result to 325. A separate opened-bank hindsight analysis found that choosing four AST expansions jointly with eight query calls could reach 994 across 30 development banks, versus 984 for random four with oracle query placement. That ten-choice ceiling is small and uses unavailable final labels. It motivated this fresh test but did not establish that public features can reliably realize the gain.

## Verification and remaining work

The protocol froze parent states, then admission pools and width choices, then both untouched transfer panels' tasks, pools, base features, ranks, selected width IDs and probe indices before opening transfer labels. The runner evaluated **201,578 candidate final labels** and predicted **577,696 AST candidate-output cells** over the admission and transfer stages; preparation took **400.5 seconds wall time** across the three stages. The **independent audit passed**: it retrained parent and child states, regenerated all 864 tasks/pools/predictions/base features and 162 bank-policy width allocations, and re-evaluated all 201,578 final candidate labels and their bank scores. Its record is `runs/ast-width-improver-transfer-20260918-v2/audit.json`.

An initial source-only run was aborted **before writing any admission files or opening labels** because a width-control constant shadowed the temperature-route map. The corrected versioned run preserves the seeds and gates and has new source/runner/protocol hashes. The aborted directory is retained as evidence, not pooled with the result.

The next seed-improver test should jointly allocate the eight output calls across all six mechanisms and select AST expansion under a declared candidate budget. The package's score must be compared with the stronger full-width cross-family allocator at matched candidate-generation, prediction and query costs. It also needs misleading-cue and new-generator transfer before broader claims. The present result rejects this learned width policy; it does not refute the fixed replay ranker or exact output sensor, and it does not establish general recursive intelligence growth.

Protocol: `EXPERIMENT-ast-width-improver-transfer.md`. Runner: `ast_width_improver_transfer.py`. Auditor: `audit_ast_width_improver_transfer.py`. Opened development: `analysis/ast-width-budget-development-20260918.json`, `analysis/ast-width-value-development-20260918.json`. Frozen versioned run: `runs/ast-width-improver-transfer-20260918-v2/`.
