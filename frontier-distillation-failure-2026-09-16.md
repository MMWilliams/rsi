# V9 failure and recovery ? 16 September 2026

The four-arm neural study stopped with CUDA out-of-memory during
`s17_corrected_first_verified_round1_candidate_final`. It did not complete the
comparison or reach deferred final scoring. The traceback cannot distinguish
peak tensors, allocator fragmentation or another allocation source.

## Preserved evidence

- Run: `runs/frontier-distillation-20260916-v9/` ? 104 preserved files.
- All 666 journal events pass chain verification; archive
  files match `analysis/frontier-v9-failure-manifest.json`.
- Four of 24 update decisions closed; five training updates completed.
- Recorded training: 240 steps, 21,572
  supervised tokens, 39.54 seconds.
- Fourteen completed sampling calls: 524,554
  generated tokens and 870.73
  seconds. The interrupted call adds unrecorded work; these are incomplete costs.
- The full search acquisition ledger and source hashes are retained in
  `analysis/frontier-v9-failure-costs.json`. Partial outcomes are not pooled into
  a completed experiment and no final samples were graded for this report.

## Recovery decision

[The v9b amendment](EXPERIMENT-v9b-resource-recovery.md) reduces generation batches
from 128 to 32 uniformly across conditions. It restarts all arms with fresh bank
seed 9162610, excluding failed-run reference templates. Training settings,
sample counts and advancement criteria remain fixed. Smaller batches can change
sampled outputs, so this is a new run rather than bit-identical continuation.

Recovery run `frontier-distillation-20260916-v9b` is in progress. The independent
auditor must pass before any completed neural comparison is reported. A separate
observer records GPU 1 memory and utilization every ten seconds in
`analysis/frontier-v9b-runtime.jsonl`, starting during initial base sampling.
This is device-wide sampled telemetry; it can miss brief peaks and does not
isolate allocator causes. It writes outside the frozen experiment archive.

This resource correction is human-directed engineering. The RSI objective and
its four mission areas remain unchanged; this failed run supplies no new RSI
claim or application-domain capability evidence.
