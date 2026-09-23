# V20 visible-constant synthesis result

V20 extended the CEGIS substrate with a small program-synthesis primitive:
enumerate multi-character substrings shared by all visible targets and admit
them as constant transitions. This generalizes the V19 observation that a
neural proposal can discover a separator such as `'- '`, while remaining
visible-only and independent of the hidden labels.

On a fresh 24-task bank:

| Condition | Correct |
| --- | ---: |
| Progressive baseline | 15/24 |
| Partial-empty control | 16/24 |
| Exact CEGIS without synthesized constants | 16/24 |
| CEGIS with visible-constant synthesis | 17/24 |
| Neural-seeded constant CEGIS, pre/post update | 17/24 / 17/24 |

The counterfactual isolated one additional task: the constant synthesizer
replaced a wrong three-atom program with `Concat(Sub(M(LOWER,2,start),C-4),
' -')`, which passed all hidden examples. This is a small but concrete search-
space expansion, not merely a ranking change.

The learning update again did not change final CEGIS coverage. The algorithmic
substrate supplied the gain; verified distillation supplied no additional
generalization in this run. The sealed archive audit passed, rechecking 888
selected/sample programs and 17 verified training rows.

The result remains bounded by the DSL, four-atom limit, visible-example
intersection, and finite task bank. It is evidence of a stronger synthesizer,
not evidence that RSI has been achieved.
