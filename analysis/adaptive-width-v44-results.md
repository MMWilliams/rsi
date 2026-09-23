# V44 adaptive search-width controller

Status: audited two-seed efficiency result. The controller first runs width-2 search and escalates to width 3 only when the visible search returns no candidate. Fixed-width controls and several visible-context policies were compared.

| Seed | Width 2 final | Width 3 final | Empty-fallback final | Mean width: fixed 3 → fallback |
| --- | ---: | ---: | ---: | ---: |
| 2026091890 | 16/24 | 16/24 | 16/24 | 3.00 → 2.04 |
| 2026091891 | 13/24 | 19/24 | 19/24 | 3.00 → 2.33 |

Across both banks, fallback preserved fixed-width-3 performance at 35/48 while using mean width 2.19 instead of 3.00. The signal is resource efficiency, not capability growth: the controller allocates extra search only when visible uncertainty is maximal.

Both runs passed independent replay audits, covering 648 policy/split rows per run and 19 sealed artifacts per run. The policy grid and resource widths remain researcher-specified.

Artifacts: `runs/adaptive-width-v44-20260917/` and `runs/adaptive-width-v44-20260918-seed91/`.
