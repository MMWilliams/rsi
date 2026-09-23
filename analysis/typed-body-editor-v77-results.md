# V77: typed internal body editing and low-level invention

## Research question

Can the system move beyond retaining or composing macro outputs by proposing new serialized stack bodies from typed low-level fragments, including shift/or bit mixing, while using only visible examples for selection?

## Protocol

Development tasks used `macro_transition`; admission and final tasks used the separate `novel_operator_transition` family. The controls were legacy ordinal grammar, direct V73 stack grammar, and V74/V75 visible-only macro replay. The `body_editor` arm exposed serialized `bit_reduce` and `bitmix` fragments, including `shl`, `shr`, and `or`, and selected candidates by visible behavior. Macro ids were retained as provenance, not as hidden labels.

## Findings

| seed | arm | development | admission | final |
|---:|---|---:|---:|---:|
| 2026092501 | legacy | 12/24 | 8/24 | 7/24 |
| 2026092501 | direct grammar | 24/24 | 16/24 | 20/24 |
| 2026092501 | mined macro | 24/24 | 16/24 | 20/24 |
| 2026092501 | typed body editor | 19/24 | 16/24 | 20/24 |
| 2026092502 | legacy | 9/24 | 9/24 | 8/24 |
| 2026092502 | direct grammar | 24/24 | 15/24 | 19/24 |
| 2026092502 | mined macro | 24/24 | 15/24 | 19/24 |
| 2026092502 | typed body editor | 12/24 | 15/24 | 19/24 |

The body editor passed admission in both replications and matched direct/replayed performance on final. It did not exceed them, so instruction-level invention recovered existing behavior but did not yet produce a measurable new capability.

## Interpretation

V77 advances the substrate from output-level macro composition to serialized internal body proposals. The stable result suggests that low-level instruction invention is reachable, but the current fragment grammar is still acting as a second solver rather than a self-improving extension of the retained library. The next step is to let the editor mutate internal bodies directly and retain successful edits across generations.

## Limitations

The fragment families, operator vocabulary, width bounds, visible alignment, cross-family relationship, and admission gate remain researcher-authored. The current editor does not yet perform true parent-body grow/delete/splice mutation; it invokes a bounded typed stack proposer with macro provenance. This is bounded RSI evidence, not open-ended self-improvement.

## Verification

Both independent audits passed, replaying 288 arm-task rows and checking 23 sealed artifacts per run. Archives: `runs/typed-body-editor-v77-20260925` and `runs/typed-body-editor-v77-20260926`.
