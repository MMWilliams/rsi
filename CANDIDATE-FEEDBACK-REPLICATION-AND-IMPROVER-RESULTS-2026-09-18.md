# Incremental evaluator feedback and inherited edit effects

Status: **fixed candidate reranking remains supported; incremental E1 promotion and child-improver growth failed their declared gates.** Both experiments were frozen before the new final labels were opened. The 12-bank source, model, pool, prediction, allocation and final-label replay passed independently; the separate parent/child reconstruction passed.

## What was tested

The same 576 new synthetic string/program tasks (seeds 902522-902533; six public mechanisms) were solved from identical frozen candidate pools. E0 was the previously supported 15-leaf top-20 candidate reranker trained on 576 earlier verified tasks and 11,282 candidate labels. E1 used the same rule plus 288 earlier verified tasks, for 864 tasks and 16,948 candidate labels. Neither checkpoint changed the generator. The first-query probe and eight-call-per-bank allocator were frozen and identical for all rankers. A 7-leaf model, a within-task label-scrambled model and the old ranker were controls. See `EXPERIMENT-candidate-reranker-replication.md`.

Separately, four bounded parents inherited different portions of the audited 576-task typed edit-effect ledger: 288 initial records; all 576 later records; 288 intact plus 288 family-preserving scrambled records; and 288 intact records duplicated. Each parent used the same researcher-written rule to produce a child: choose a public-family ranker route from verified success counts, then fit a ridge first-query-gain forecast and spend eight calls per bank. Child routes, coefficients and call IDs were frozen before new final labels were opened. The first six new banks were admission, and the final six were protected transfer. See `EXPERIMENT-candidate-edit-improver-transfer.md`.

## Fresh evaluator replication

| Ranker | Correct without calls / 576 | Correct with 96 shared calls / 576 |
| --- | ---: | ---: |
| Old | 291 | 328 |
| E0 | 326 | **352** |
| E1 | **331** | 351 |
| 7-leaf control | 315 | 337 |
| Scrambled-label control | 214 | 251 |

E1 minus E0 was **+5 without calls**, with five positive banks, two losing banks and paired exact bank-bootstrap interval [-3,+13]. The preregistered gate required at least +8, eight positive banks and a positive lower endpoint; E1 also trailed E0 by one with the shared call budget. It failed. Across the opened first and fresh second panels, E1 minus E0 totals +16/1,152 without calls (descriptive paired 24-bank interval [+3,+29]), but only +1/1,152 at the shared 192-call budget. The pooled result does not replace the failed new-panel gate.

The family-level self-edit fallback was selected from opened data and then frozen for this panel. Routing self-edit tasks to old and all others to E1 yielded 336 versus 331 zero-call choices (+5, interval [-1,+11]) and 357 versus 351 with the same 96 calls (+6, interval [+1,+12]). Its preregistered rule required a positive *zero-call* lower endpoint, so it too remains unpromoted. The repeated direction is useful development evidence, but the zero-call gain is too sparse across banks to satisfy the rule.

Full-pool reachability was 501/576; old top-20 reachability was 442/576. These are generator/shortlist ceilings, separate from evaluator correctness. Preparation generated 101,312 base candidates and 35,030 added AST candidates, rescored 11,380 top-20 candidates and predicted 1,090,736 candidate/probe outputs. The research oracle scored 136,342 final candidate labels; each budgeted policy spent 96 true output calls. Preparation wall time was 304.1 seconds, with 1,453.3 summed candidate-generation seconds. Historical candidate-label acquisition, model fitting and inference are additional costs.

## Same-base improver transfer

All four parents selected the same public-family ranker route: E1 for five families and old for self-edit. Their children differ only in forecast coefficients and call locations. Thus this test isolates the effect of additional feedback on query allocation under this bounded rule.

| Child policy | Admission 6 banks / 288 | Protected transfer 6 banks / 288 | All 12 / 576 |
| --- | ---: | ---: | ---: |
| Initial, 288 effect records | 173 | 178 | 351 |
| Later, 576 records | 173 | **182** | 355 |
| Scrambled additional records | 176 | 180 | **356** |
| Duplicated initial records | 173 | 178 | 351 |
| Fixed E1 with existing allocator | **179** | 172 | 351 |

The later child gained +4 over the initial child on protected transfer, with three positive banks, no losses and paired interval [+1,+8]. This is a promising *component observation*, but the preregistered admission gate rejected the later child because it scored 173 versus the fixed E1 control's 179. The transfer gate also required four positive banks and was missed. Across all 12 banks, the scrambled child scored one higher than the later child. **No improved child improver is established.** All children used 96 true output calls, with the same candidate and prediction work on the target bank. The later parent consumed 288 additional historical effect records; acquiring those records required verified candidate and output counterfactuals that cannot be treated as free.

The later child's first-query-gain forecast MSE was 0.12272 versus initial 0.12417; the scrambled control was 0.12360. Selected query gains were 19, 15 and 20, respectively. Unavailable hindsight placement for each child's identical ranker route could gain 77, so selected-gain regret was 58 for later, 62 for initial and 57 for scrambled. Better average forecast error produced a small realized decision gain over initial but did not clear the control or admission tests. The old fixed call allocation combined with the self-edit route scored 357 on all 12 banks, also above the later child's 355; that combination is an opened-label analysis and not a promoted policy.

## Audit and decision

The independent replication audit rebuilt 864 source tasks, rechecked 16,948 source candidate labels and public feature rows, retrained all four models, regenerated all 576 new tasks/pools, rechecked 11,380 rerankings, 1,090,736 output predictions, 12 allocations, 136,342 final candidate labels and 180 bank-policy scores. The child-policy audit reconstructed 2,016 source row uses and 2,304 target decisions. Both passed.

Keep **E0** as the supported fixed-pool reranker component, with its original fresh +39/576 versus old and this panel's +35/576. Keep E1, the self-edit fallback and the inherited query controller in shadow. The next development target is conditional query value **after** reranking: the first output's marginal value fell as rank selection improved, and the current controller recovered only 19 of 77 possible query fixes at its own fixed route. Any next checkpoint should be frozen and tested on a third disjoint bank with admission and child transfer; no additional rules should be chosen from this opened bank and called validation.

Machine-readable evidence: `runs/candidate-reranker-replication-20260918/replication_report.json`, `runs/candidate-reranker-replication-20260918/improver_results.json`, `runs/candidate-reranker-replication-20260918/audit.json`, `runs/candidate-reranker-replication-20260918/improver_frozen.json`.
