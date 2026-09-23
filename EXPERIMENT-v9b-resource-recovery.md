# V9b: resource recovery for verified-frontier distillation

Declared on 16 September 2026 after the v9 process terminated with a CUDA
out-of-memory error, before generating this run's banks or inspecting final
scores. This amendment incorporates `EXPERIMENT-v9-frontier-distillation.md`
except for the two configuration changes below.

## Incident and interpretation

`runs/frontier-distillation-20260916-v9/FAILED.json` records failure during
`s17_corrected_first_verified_round1_candidate_final` sampling. The process
exited with code 1. Four update decisions had closed; the fifth candidate had
finished training and admission sampling. Final scoring had not begun.
This incomplete study supplies no completed four-arm research comparison.

The recorded exception establishes an allocation failure. It does not establish
whether peak live tensors, allocator fragmentation or competing allocations
caused it; no per-batch memory trace was captured. GPU 1 was idle after process
exit. GPU 0 is occupied by other work and is not used for this experiment.

## Predeclared changes

- Reduce generation batch size from 128 to **32**, uniformly for every arm,
  seed, base and bootstrap evaluation. Keep 64 samples per task, maximum 96 new
  tokens and all decoding parameters unchanged. This reduces concurrent tensor
  memory. Batching can change random-number consumption and floating-point
  behavior, so this is not a bit-identical continuation.
- Set fresh bank seed **9162610**. The runner excludes templates from all prior
  protected banks, including the failed v9 bank. Preserve the same split sizes,
  training seeds, checkpoint, training schedule, four controls and advancement
  criteria. Begin a new run and redo every arm consistently.

No admission threshold, checkpoint, harvest policy or final metric is selected
using the failed run's final outcomes. Its raw files and source snapshots remain
preserved. Do not pool its partial results with this study. The repeated compute
is a recovery cost, separate from this run's ledger; the failed study's partial
ledger cannot account for every token of its interrupted sampling call.

## Verification and limits

Use the existing frozen runner and independent auditor, with this document as
the archived protocol. The original v9 protocol remains available in the failed
run's source snapshot and in the project. All final scoring remains deferred
until 24 decisions close. Audit completion is required before reporting results
as verified. Lower batching is a resource intervention, not an RSI improvement.

The goal remains a system that improves its improver for research, cybersecurity,
social good and policy. This DSL study tests one training component; it does not
establish performance or suitability in those application domains.

Incorporated v9 protocol SHA-256: `1f862c8a84a26df6e443cd70bf3b6aa9f5323aa759786478bc34e2c1fdf3b048`.
