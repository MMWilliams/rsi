# Sharp-ranker transfer to withheld mechanisms

## Decision

**Do not extend the temperature-0.25 evaluator claim to withheld mechanisms.** It beat temperature 1.0 on the three families used for source training, **105/144 versus 95/144**, but on the three withheld families scored **32/144 versus 33/144**; temperature 0.5 scored **37/144**. The withheld-family bank differences for 0.25 minus 1.0 were **+1, −2, 0, +1, 0, −1**, with an exact six-bank resampling 95% interval of **−6 to +4**. The predeclared transfer gate failed. The 288-task reconstruction audit passed.

All rankers saw the same 48,764 candidate programs, one visible example per task, no inference output queries, and 15 final examples. The 0.25 and 1.0 models used the same 31,500 verified source candidate labels, architecture, initialization and 120 training epochs. Each of six new banks contributed eight tasks per family.

| Mechanism | Correct pool / 48 | Temp 0.25 | Temp 0.5 | Temp 1.0 | E192 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Transformation, withheld | 48 | 14 | **22** | 21 | 21 |
| AST, withheld | 14 | 0 | 0 | 0 | 0 |
| Novel operator, withheld | 35 | **18** | 15 | 12 | 11 |
| Stack, trained | 48 | **36** | 30 | 29 | 25 |
| Mutation, trained | 48 | **32** | 31 | 30 | 29 |
| Self-edit, trained | 48 | 37 | **38** | 36 | 20 |
| **All 288 tasks** | **241** | **137** | 136 | 128 | 106 |

The aggregate 0.25 lead hides two different failures. On transformation tasks it lost seven choices to temperature 1.0 and eight to 0.5 despite full candidate reachability. On novel-operator tasks it gained six over 1.0. AST had only 14/48 reachable pools, and no evaluator selected a correct program even among those 14. AST therefore needs both a better candidate generator and a representation or evaluator that can identify reachable correct programs. A selector among the existing temperatures cannot repair AST.

The audit regenerated all 288 tasks and candidate pools, independently recomputed 1,728 model/control choices and every final outcome. It passed. Protocol: `EXPERIMENT-temperature-withheld-families.md`. Runner, audit and data: `temperature_withheld_families.py`, `audit_temperature_withheld_families.py`, `runs/temperature-withheld-families-20260917/`.

## Seed-improver implication

The strongest supported zero-query evaluator depends on mechanism. A fixed global 0.25 model is defensible for the three trained families and promising for novel operators, while transformation favors 0.5 or 1.0 in this trial. Those family choices are now inspected development evidence and require new banks before promotion. A seed improver should carry **contextual edit effects**, verify them on protected admission tasks, and roll back harmful substitutions. It should treat low reachability as a candidate-generation incident, not an evaluator error or an excuse to claim a ranker gain. The next parent/child test should ask whether inherited family-specific edit knowledge creates a better child policy than an empty or scrambled state at the same live feedback budget.
