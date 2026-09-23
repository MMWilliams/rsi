# Sharper listwise feedback: frozen evaluator transfer

## Decision

**Promote temperature 0.25 as a supported evaluator edit on this synthetic fixed-pool distribution.** The training-rule edit passed its predeclared fresh-bank gate: 143/192 correct top choices against the original temperature-1 listwise evaluator's 130/192, positive gains on five of six banks with one tie, an exact six-bank resampling 95% interval of **+6 to +19 choices per 192**, and higher aggregate accuracy than every tested control. The independent reconstruction audit passed. This is an evaluator improvement, not yet a better improver or recursive growth.

## Edit and evidence

Both models used the same 192 source tasks, **31,500 exact-verifier candidate labels**, 175→32→1 ReLU architecture, initialization, AdamW settings, and 120 training epochs. The single edit lowered the listwise loss temperature from 1.0 to 0.25. It makes high-ranked incorrect candidates matter more in the gradient, matching the top-choice endpoint. Development scores on previously inspected targets were 149/192 at 0.25, 143/192 at 0.5, 130/192 at 1.0, 123/192 at 2.0, and 118/192 at 4.0. Those scores selected the 0.25 checkpoint before the fresh bank seeds were generated.

Six untouched 32-task banks, seeds 902234–902239, used the same one-visible-example, two-source candidate-pool contract as the prior listwise transfer. Eight probe inputs were unused; final scoring used 15 held-out examples. There were no inference oracle output queries. Reachability was 190/192.

| Evaluator | Correct / 192 |
| --- | ---: |
| E192 independent classifier | 98 |
| Context blend | 107 |
| Original listwise, temperature 1.0, 120 epochs | 130 |
| Intermediate temperature 0.5, 120 epochs | 137 |
| Temperature 0.25, 80 epochs | 136 |
| **Temperature 0.25, 120 epochs** | **143** |

The primary bank differences versus temperature 1.0 were **+3, +3, +4, +1, +2, 0**. By mechanism, temperature 0.25 versus 1.0 was stack **48/66 versus 42/66**, mutation **43/66 versus 40/66**, and self-edit **52/60 versus 48/60**. The edit therefore improved all three tested mechanisms in aggregate. Its six-task aggregate edge over temperature 0.5 is smaller and not a separate strong transfer claim.

The 192-task audit regenerated every candidate pool, independently recomputed 768 temperature-checkpoint choices, and checked every final outcome. All choices were frozen before final labels were opened. This is an auditable prepare/score boundary, not independent host access control. Passing the 15 final examples is a finite synthetic correctness test, not universal program equivalence.

Protocol: `EXPERIMENT-temperature-ranker-transfer.md`. Training search: `temperature_ranker_development.py`, `analysis/temperature-ranker-development.json`. Runner and audit: `temperature_ranker_transfer.py`, `audit_temperature_ranker_transfer.py`. Frozen data: `runs/temperature-ranker-transfer-20260917/`.

## Improver implication

This is a useful **edit type** for the seed improver: changing the evaluator's training objective can produce a larger transferable gain than simply fine-tuning its weights on one more verified bank. The previous one-bank weight-update pilot scored at most 130/192 against a fixed 130/192, whereas the loss edit scored 143/192 on a separate fresh test. The two studies used different target banks, so this is a direction for the edit catalog rather than a direct paired comparison between those experiments.

The next test must make edit selection automatic: give improver checkpoints the same catalog, source labels, admission feedback, model-training budget, and identical base evaluator; compare their choices and final-bank gains. Then test whether a later checkpoint can produce a child improver that outperforms one produced by the initial checkpoint on a second untouched bank. Until then, the loss edit is researcher-authored and the improver-growth claim remains open.
