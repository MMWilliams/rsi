# V21 architecture evolution: admission-gated substrate selection

Status: audited exploratory finding. This is a component result, not a demonstration of recursive self-improvement.

## Result

The run evolved a bounded search architecture using a development split and a separate admission split. The gate required admission accuracy not to decrease and allowed at most two development tasks of regression. The selected architecture was CEGIS with visible constant synthesis:

| Architecture | Development | Admission | Fresh final |
| --- | ---: | ---: | ---: |
| Baseline progressive search | 19/24 | 18/24 | 13/24 |
| Selected CEGIS + visible constants | 22/24 | 20/24 | 17/24 |

The final improvement was +4/24 tasks, or +16.7 percentage points, on a fresh 24-task bank. In the admission slice, CEGIS without constant synthesis also reached 22/24 and 20/24; the selected constant-synthesis variant won the deterministic architecture-ID tie-break. Thus the result identifies a CEGIS substrate gain, but does not isolate a unique benefit from constants in this run.

## What this shows

An admission-priority architecture gate can retain a search-substrate change that is stronger than the baseline on both development and admission data, then carry it to a fresh final bank. This is stronger evidence than selecting on one development split alone, but it is still bounded algorithm engineering: the catalog was hand-designed, the DSL and oracle were fixed, and no learned proposer invented the architecture.

## Audit and limitations

The independent audit replayed 528 stored task evaluations, checked deterministic replay, recomputed oracle correctness, verified the generation selection chain, checked the journal binding, and verified 21 sealed artifacts. Audit status: passed.

Main limitations: one fresh bank of 24 final tasks; one architecture generation after the baseline; a small hand-authored mutation neighborhood; same-host oracle execution; fixed DSL; no total-compute normalization across architectures; and no evidence that the system can autonomously improve its own improver. The final gain should therefore be reported as a replicated-in-run CEGIS substrate improvement, not as RSI.

Artifacts: `runs/architecture-evolution-v21-20260917/results.json`, `runs/architecture-evolution-v21-20260917/audit.json`, and `runs/architecture-evolution-v21-20260917/`.
