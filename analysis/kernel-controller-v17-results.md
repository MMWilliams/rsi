# V17 search-kernel controller result

This experiment changed the improver's substrate rather than its numeric
costs. Three symbolic kernels were evaluated on development and final banks:
the baseline cost-reopening search, a partial-empty atom pool, and a state-
reopening variant. A visible-feature nearest-neighbor controller selected a
kernel per final task using development outcomes only.

| Run | Baseline | Partial-empty | Reopen | Controller |
| --- | ---: | ---: | ---: | ---: |
| `kernel-controller-v17-20260917` | 15/24 | 16/24 | 15/24 | 16/24 |
| `kernel-controller-v17b-20260917` | 18/24 | 16/24 | 18/24 | 18/24 |

The controller matched the best fixed kernel on both fresh banks, avoiding a
selection loss, but did not exceed the best fixed kernel. The partial-empty
kernel's +1 result in the first bank did not replicate in the second bank.
Both archives passed audit: 144 kernel rows replayed per run and all 24
controller choices reconstructed from visible features.

This is evidence that algorithm-substrate selection is feasible and safer
than promoting one learned kernel globally, but it is not yet recursive
self-improvement. The portfolio remains fixed, the controller uses a small
hand-designed feature vector, and no new algorithm was invented.
