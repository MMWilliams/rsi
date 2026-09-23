# V13 contextual policy selector result

A visible-feature nearest-neighbor controller was trained on one development
bank to choose between the base and evolved search policies per final task.
The controller used no final hidden labels during selection.

| Selector | Final selected correct | Final coverage@64 |
| --- | ---: | ---: |
| Fixed base | 14/24 | 16/24 |
| Fixed evolved | 16/24 | 18/24 |
| Contextual nearest-neighbor | 14/24 | 16/24 |

The contextual controller did not improve over either fixed policy on this
split. This is a useful null result: visible task features and a small
development bank were insufficient to reliably choose between policies.
