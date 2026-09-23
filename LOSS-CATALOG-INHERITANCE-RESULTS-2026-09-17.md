# Inherited edit-effect table: parent and child trial

## Decision

**No improver-growth promotion.** An inherited table of verified loss-edit outcomes helped the first parent policy select a better evaluator on a small admission sample, but did not improve the child policy after both had seen the same new verified bank. On six untouched parent/child episode pairs, parent final accuracy was **71/96** for inherited versus **64/96** for empty. Child final accuracy was **69/96** for inherited versus **70/96** for empty and **69/96** for fixed temperature 0.25. The predeclared child-growth gate failed.

## Fixed setup

The common edit catalog contained three 120-epoch rankers, trained on the same 31,500 source candidate labels at listwise loss temperatures 1.0, 0.5, and 0.25. Each episode used a 32-task parent bank and a separate 32-task child bank. The first 16 tasks of each supplied verified admission outcomes for all three catalog choices; the final 16 measured the chosen edit. After freezing each parent final choice, all 32 parent task outcomes updated the edit-effect table before child admission and final choice. All policies shared the same candidate pools, model training, admission labels, and live evaluation budget.

The inherited table came from the previous six-bank temperature trial: 130/192 for temperature 1.0, 137/192 for 0.5, and 143/192 for 0.25. It was discounted to 64 effective tasks. Empty started at zero; scrambled inheritance used the same prior values assigned cyclically to the wrong edit names. The historical table has a separate acquisition cost. The previous study actually scored all 30,902 candidate programs for its broader audit; the table itself needed only the 301 distinct top-choice programs from the three models.

| Policy | Parent final / 96 | Child final / 96 |
| --- | ---: | ---: |
| Empty table | 64 | **70** |
| Inherited table | **71** | 69 |
| Scrambled table | 66 | 64 |
| Fixed temperature 1.0 | 65 | 60 |
| Fixed temperature 0.5 | 66 | 68 |
| Fixed temperature 0.25 | **71** | 69 |

The child inherited-minus-empty differences by episode were **0, 0, 0, 0, −1, 0**. Inheritance therefore did not produce a better child improver. The inherited parent simply selected fixed temperature 0.25 in all six episodes; its parent advantage did not exceed that fixed policy. The empty policy learned enough from its parent bank to choose temperature 0.25 on five child banks and temperature 0.5 on one, where 0.5 gained a task. This is limited evidence of initial label efficiency, not a positive feedback loop that compounds.

A development-only replay varied prior equivalent size from 0 to 192 tasks and decayed the prior after the parent bank. Child totals stayed **69 or 70/96**. No sensitivity setting generated a child gain over empty. This is evidence against repairing this catalog policy by prior-weight tuning alone; it is not a fresh confirmation for any alternative setting.

## Validation and scope

The 384-task reconstruction audit passed. It regenerated every candidate pool, recomputed 1,152 model choices, replayed parent admission, frozen parent choices, full parent updates, child admission, frozen child choices, and every final outcome. Live feedback required 449 distinct selected-program evaluations before child final, plus 146 on child final; with 15 final examples per program this represents up to 8,925 example checks. Candidate generation produced 61,956 programs. The source labels and three trained models are common costs; the inherited table's prior acquisition is additional historical cost.

Protocol: `EXPERIMENT-loss-catalog-inheritance.md`. Runner and audit: `loss_catalog_inheritance.py`, `audit_loss_catalog_inheritance.py`. Data: `runs/loss-catalog-inheritance-20260917/`. Prior-strength sensitivity: `loss_catalog_weight_development.py`, `analysis/loss-catalog-weight-development.json`.

## Next edit

The fixed global table can remember that temperature 0.25 is usually strongest, but it cannot predict when a different edit will work or create a new kind of edit. The next seed-improver test should evaluate **contextual edit effects and edit creation**, with disjoint admission and child banks and the fixed 0.25 ranker as a strong control. A future gain must beat this control at matched compute and show that a later parent produces a better child improver from the same base; this trial does not.
