# V22 AutoML architecture search: larger substrate gain

Status: audited exploratory finding. This result is evidence of automated algorithm selection, not proof of recursive self-improvement.

## Protocol

The improver generated 180 unique architectures from a declarative factorial space over engine (`baseline`, `partial`, `cegis`), search budget, atom depth, visible constant synthesis, progress weighting, and widening. It used Pareto successive halving:

1. screen all 180 candidates on 8 development tasks;
2. promote 16 to the full 24-task development split;
3. promote 6 to the 24-task admission split;
4. select by admission non-regression plus a two-task development tolerance;
5. score the retained architecture once on a fresh 24-task final bank.

The final bank was not used for promotion.

## Result

| Architecture | Development | Admission | Fresh final |
| --- | ---: | ---: | ---: |
| Baseline progressive search | 13/24 | 10/24 | 12/24 |
| AutoML champion: CEGIS, depth 6, visible constants | 21/24 | 14/24 | 19/24 |

The fresh-bank gain was +7 tasks, or +29.2 percentage points. CEGIS with depth 4 and visible constants tied the selected depth-6 architecture at 19/24 on the final bank; depth 6 was retained by the pre-registered deterministic tie-break. This means the robust finding is the CEGIS substrate family, not a uniquely identified depth setting.

## Audit

The independent audit replayed all 2,040 stored task evaluations, recomputed oracle correctness, regenerated the 180-candidate space, recomputed every successive-halving promotion, recomputed the admission decision, verified the journal binding, and checked 27 sealed artifacts. Audit status: passed.

## Interpretation and limitations

This is the strongest current result for automated improver selection: the system searched a materially larger architecture space and retained a search substrate that generalized to a fresh bank. It still does not establish RSI. The candidate space and factor ranges were authored by the researcher; the DSL and oracle were fixed; the banks are small; successive halving can discard low-fidelity winners; the architecture is not learned from its own source code; and there is no evidence of an open-ended, autonomous improvement cycle.

The paper should frame this as “automated search-substrate selection produces a large bounded capability gain” and reserve “recursive self-improvement” for a future test in which the system independently expands or repairs its own hypothesis space and replicates the gain across fresh banks.

Artifacts: `runs/automl-architecture-v22-20260917/results.json`, `runs/automl-architecture-v22-20260917/audit.json`, and `runs/automl-architecture-v22-20260917/`.
