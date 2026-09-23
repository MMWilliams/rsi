# Contextual loss-edit table: parent and child transfer

## Decision

**No growing improver was confirmed.** An inherited family-specific table of verified evaluator-edit effects scored **73/144** child final tasks versus **72/144** for an empty table and **71/144** for a family-scrambled table. The fixed family map from the prior inspected bank scored **74/144**. Inherited minus empty was **0, 0, 0, +1, 0, 0** by episode, with an exact six-episode resampling 95% interval of **0 to +3**. The predeclared five-bank, positive-interval, and strongest-fixed gates failed. The 576-task reconstruction audit passed.

## Common base and measured effects

Six independent episode pairs each used a 48-task parent bank and a separate 48-task child bank, with eight tasks per mechanism. Each bank's first 24 tasks supplied equal verified admission feedback for all three 120-epoch listwise evaluators (loss temperatures 0.25, 0.5, and 1.0); the last 24 were the policy outcome. All policies shared candidate pools, source model labels, live admission labels, and zero inference output queries. The inherited table used the earlier six-family trial's outcomes discounted to eight effective tasks per family. Its historical acquisition cost is separate.

| Policy | Parent final / 144 | Child final / 144 |
| --- | ---: | ---: |
| Empty family table | 64 | 72 |
| Inherited family table | 66 | 73 |
| Scrambled family table | 64 | 71 |
| Fixed prior best by family | **68** | **74** |
| Fixed temperature 0.25 | 66 | 71 |
| Fixed temperature 0.5 | 65 | 70 |
| Fixed temperature 1.0 | 56 | 69 |

The inherited policy's only child advantage over empty was one transformation task. On the child final bank, candidate reachability was **119/144**. AST was reachable on only **6/24** child final tasks and every policy scored **0/24** there. Fixed temperature selection among these rankers cannot fix that mechanism.

The audit regenerated all 576 tasks and 97,460 candidate programs, recomputed 2,304 model/control choices, replayed parent admission, frozen parent choices, full parent updates, child admission, frozen child choices, and every final outcome. It passed. Live feedback required 685 distinct selected-program evaluations before child final and 225 on child final, with up to 15 example checks per evaluation. The inherited prior required the separate earlier six-family trial.

Protocol: `EXPERIMENT-contextual-loss-inheritance.md`. Runner, audit and data: `contextual_loss_inheritance.py`, `audit_contextual_loss_inheritance.py`, `runs/contextual-loss-inheritance-20260917/`.

## What changes next

The family table captured a real contextual pattern, but the fixed map already captured it and the new table did not compound through a child. The next seed needs an edit vocabulary that changes the candidate set or representation, then separately tests evaluator ranking on the new fixed pools. AST is the clearest target: expand and verify candidate generation first, then train and transfer an AST-capable evaluator. Protected admission, rollback, matched cost, and a second child-improver bank remain required before a positive RSI claim.
