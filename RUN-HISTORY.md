# Pilot run history

All runs below are retained under `runs/`. Failed and interrupted runs were not overwritten.

Ten-version stitch pilots `stitch-ten-pilot-20260917b` and `stitch-ten-pilot-20260917c` completed and independently audited. The semantic source-priority router solved 10/12 on both fresh mixed-family banks versus best native arms at 8/12 and 7/12, with substantially more aggregate proposal compute. V8 in a separate DSL lane scored 9/12 versus 5/12, then 8/12 versus 8/12. The initial `stitch-ten-pilot-20260917` archive failed its source-integrity gate after a concurrent `evolving_domain.py` change and is excluded. See `STITCH-TEN-PILOT-RESULTS-2026-09-17.md`.

V12 credit transfer `credit-transfer-20260917-v12` completed under the frozen matched-compute protocol. Six conditions and six source groups used a common 256-task final bank. Immediate-only averaged 59.77%; observational-descendant and paired-credit tied it in every group; scrambled and random were -0.78 pp, and empty was -0.39 pp. The engineering screen failed. Independent audit passed 2,274 events, 544 regenerated tasks, 525 unique batches and replays, and 13,792 strict-oracle rows. See `credit-transfer-results-2026-09-17.md`.

Neural follow-up `frontier-distillation-20260916-v9` failed with CUDA memory
exhaustion after four of 24 decisions; the fifth candidate finished training.
Final scoring had not begun. Preserve its 104 files and external failure manifest
`analysis/frontier-v9-failure-manifest.json`. No completed comparison exists.
Recovery `frontier-distillation-20260916-v9b` is running with generation batch
size 32, fresh bank seed 9162610, and the same four arms, three seeds and two
rounds. See `EXPERIMENT-v9b-resource-recovery.md`; partial results are not pooled.

Paired source-credit probe `paired-credit-20260916-v10` completed its runner from a protocol
declared before fresh task generation. Six groups each compare twelve numeric
initial edits against a shared no-edit branch under the same two-round downstream
schedule; all measurement is deferred until branch optimization closes. A separate
10-task implementation fixture passed independent audit (278 unique searches and
exact replays, 13 reconstructed branches, 12 recomputed pairs) and five focused
tests. Fixture effects have no research status. See C022 and
`EXPERIMENT-v10-paired-credit-probe.md`. V10's independent audit passed: 7,376
unique searches and exact replays, 78 branches, 72 effects. Ten of 72 pairs had
nonzero later-improvement effects, including eight positive and two negative.
This source headroom does not test an inherited selector or establish RSI.

V9b closed all 24 neural decisions, but the fresh independent audit stopped on
a visible-behavior diversity mismatch. A saved output using `M(WORD,1,End)`
executes under the published interpreter but is rejected by the strict host
oracle. The failed audit prevented report publication. Preserve the archive and
do not treat the runner's advancement screen as verified; see C023. A posthoc
scan of 198,656 saved outputs found 106 visible behavior disagreements and three
trailing-comma programs accepted by the old oracle but rejected by the canonical
published grammar. The oracle now rejects trailing commas, regression tests pass,
and a fresh neural rerun is required.

V11 `frontier-distillation-20260916-v11` launched after the contract repair with
fresh bank seed 9162612, the repaired strict oracle/auditor, and all prior
protected-bank template exclusions. It uses the same four-arm, three-seed,
two-round design as V9b. No partial result is evidence; require the fresh audit
before interpreting any score or advancement screen. See C024.

V11 completed and passed independent and report-time audits. Its screen failed:
corrected-frontier minus corrected-selected selected-round-two pass@64 was -0.52
points, positive in one of three seeds, and below frozen bootstrap. Corrected
first-verified reached 22.40% mean pass@64; corrected frontier reached 20.31%.
The full audit reconciled 221,184 raw samples, 10,122 training rows, 1,152
optimizer steps and 24 decisions. Preserve the negative result and do not
retrospectively promote a checkpoint. See C025 and `STATUS-2026-09-17.md`.

V12 is staged but not launched. Its protocol compares immediate-only,
observational-descendant and paired later-improvement credit, plus scrambled,
empty and random controls, using the audited V10 source evidence on fresh
transfer tasks. Selector implementation and table-construction tests passed;
the full suite is 141 passed. The runner and independent auditor are the next
implementation gate. See C026 and `EXPERIMENT-v12-credit-transfer.md`.
Before launch, the full suite passed 65 tests and a small GPU fixture passed its
independent audit. Four additional auditor tests passed, including three
semantic forgeries with reconstructed hashes. Fixtures are implementation checks,
not study replications. Details: C017-C019 in `CHANGE-REGISTER.md`.

Fresh search validation: `search-validation-20260916-v8` completed in 297.03
seconds. Six new seed groups / 576 tasks, four budgets and a fixed mixture.
Corrected@128 first-choice correctness 332 -> 377 and coverage@64 374 -> 438;
joint improvements in 5/6 groups passed the declared screen. Actual costs rose
at equal ceilings; 17 first-choice regressions remain. Audit regenerated every
task, reexecuted 4,608 searches and regraded 66,680 frontier programs. Full suite:
61 passed. Report: `search-validation-results-2026-09-16.md`.

Search diagnostics: `fragment-headroom-20260916-v7` completed in 9.65 seconds;
all 60 compatible source additions had zero correctness effect. Audit passed
1,536 outputs (416 fresh, 1,120 verified reuse). Then
`partial-empty-20260916-v8-diagnostic` completed in 59.36 seconds on 576 source
tasks. Correcting the partially empty atom filter raised first-choice correctness
357 -> 401 and coverage@64 398 -> 458, with 21 first-choice regressions and
63.56% more primitive charges. Audit reexecuted 1,152 searches; full suite 59
passed. Fresh replication and compute matching remain open. Report:
`search-diagnostic-results-2026-09-16.md`.

Library-proposer study: `library-inheritance-20260916-v7` completed in 903.02
seconds. Audit passed 40,512 outputs / 504 attempted edits. No fragment was
installed; all memory arms tied the ancestor at 104/192 and g6 trailed the
numeric-pair control by 1.0417 points. The screen failed. The subsequent
`reopening-diagnostic-20260916-v7` checked a cheaper-route suppression issue on
source requests only: 1,120 outputs plus replays, audited; path costs corrected
but correctness unchanged. Both results: `library-results-2026-09-16.md`.

Offline source diagnostic: `context-diagnostic-20260916-v6` completed once in
0.752 seconds of measured analysis time. Nested source folds over 864 contexts
gave contextual prediction lower MSE but unreliable ranking gains: tied
parent-only and beat unconditional means in only 1/9 sources. The declared
advancement screen failed. Audit reconstructed 891 fits and 51,840 predictions.
No new search, final-bank query or neural training occurred. Details:
`context-diagnostic-results-2026-09-16.md`.

Replication: `inheritance-20260916-v5` completed in 673.09 seconds with six new
sources and 256 final tasks. Independent audit reconciled 30,976 outputs and 792
selection/edit decisions. g6 averaged −0.20 points versus empty and −0.33 versus
random. Only 1/6 sources beat both empty and scrambled, so the declared screen
failed. See `inheritance-replication-results-2026-09-16.md`. This result does not
support promoting the current table selector as a reliably better improver.

Balanced inheritance follow-up: `inheritance-20260916-v4` completed once in
269.55 seconds and passed independent audit (13,568 search outputs, 396 edits).
g6 averaged +0.78 percentage points over empty tables but had source differences
of 0.00, +4.69 and −2.34 points; advantages over scrambled/random were +0.52.
This is a small inconsistent component signal, not demonstrated RSI. See
`inheritance-results-2026-09-16.md`. Temporary reduced-bank test fixtures are
verification artifacts, not study replications; their outputs were not analyzed
as evidence for the inheritance hypothesis.

Retention follow-up: `retention-20260916-v3` completed and audited after 532.7 seconds. Replay preserved more syntactic variety but ended at 2/24 final tasks versus fresh-only's 3/24. Both gate decisions accepted; validation missed a final-bank regression. The audit reconciled 19,968 generations, 410 training-pool rows and all checkpoint decisions. See `retention-results-2026-09-16.md`. The full RSI claim remains unsupported.

| Run | Status | What happened |
| --- | --- | --- |
| `pilot-20260916-v1` | Completed diagnostic | Raw Qwen3-0.6B produced no verified self-training data. Search distillation reached 5/24 tasks at pass@64, matching fixed-search distillation; table-transfer restarts accepted zero edits. This identified an unusable inheritance assay and a missing common model initialization. Later review also found unequal adapter precision and overlapping adapter names, so this is not the controlled neural comparison. No saved v1 model output contained the independently found `C-0` edge case. |
| `pilot-20260916-v2` | Interrupted before GPU training | Independent review found that the host oracle interpreted `C-0` differently from the published DSL. The worker was stopped, a regression test was added, and the run was preserved without final measurements. |
| `pilot-20260916-v2-fixed` | CPU stage completed; neural guard stopped run | The shared-bootstrap identity check caught a PEFT state-key collision between `search` and `fixed_search`. The initial adapter and adapters added later also had different dtypes. The completed CPU results remain usable because those components do not involve adapters. |
| `pilot-20260916-v2-complete` | Completed and audited | Uses non-overlapping internal adapter names, uniform float32 LoRA tensors, and verified identical bootstrap hashes. Reuses the completed CPU stage only after matching its source hashes, configuration, task-bank hashes, and journal chain. All 7,680 final raw samples and 179 training trajectories reconcile with the published interpreter. Coverage-compounding and inherited-improver criteria were not met. See `pilot-results-2026-09-16.md`. |

The v2 protocol was written before its final holdout evaluation. It increases the transfer assay's task batches and edit opportunities, provides a shared verified bootstrap, corrects the table's positive-effect accounting, and interleaves updated neural proposals with amplifier editing. Implementation guards found and stopped correctness problems before producing the final neural comparison. The final report must state the outcome even if adaptive search, inherited tables, or new operators fail to help.
