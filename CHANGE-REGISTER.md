# Change and evidence register

The objective remains a system that improves its own ability to improve, supported by causal tests. Infrastructure success and higher task accuracy alone do not satisfy that objective. Entries distinguish measured outcomes, explanations, and the next discriminating test.

## C028 - Run and audit V12 credit transfer

- Trigger: V10 showed sparse later-improvement headroom and V11 showed negative frontier transfer. V12 tested immediate-only, observational-descendant, paired-credit, scrambled, empty, and random selectors at matched downstream compute.
- Result: the independent audit passed 2,274 journal events, 544 regenerated tasks, 525 unique reexecuted batches plus exact replays, and 13,792 strict-oracle rows. Immediate-only averaged 59.77% on the common final bank; observational and paired credit tied it in all six groups; scrambled and random were -0.78 percentage points and empty was -0.39 points.
- Interpretation: the declared selector screen failed. The inherited credit fields did not improve edit choice in this assay. This is a component result, not evidence of RSI.
- Evidence: `runs/credit-transfer-20260917-v12/audit.json`, `credit-transfer-results-2026-09-17.md`, and `configs/credit-transfer-v12.json`.
- Limits: six groups share one final bank; the V10 table is a source-derived estimator; the DSL and edit catalog remain bounded and researcher-authored. The audit records unrelated post-run source drift outside the sealed run snapshot.
- Next: calibrate effect estimates on larger independent source banks, or retire this selector and move to another measured bottleneck; do not promote the current credit selector into the recursive loop.

## C001 — Comparable neural arms

- Trigger: v1 lacked self-training trajectories and had unequal LoRA precision and overlapping adapter names; v2-fixed's bootstrap hash guard failed.
- Change: common verified bootstrap, float32 adapter tensors, non-overlapping PEFT names, exact initial-state equality checks.
- Evidence: `tests/test_adapters.py`; `runs/pilot-20260916-v2-complete/audit.json`; archived run source.
- Result: controlled training could proceed; no RSI result. A controlled interpretation of v1's neural comparison is invalid.
- Explanation: naming and dtype affected tensor copying and training. The shared-state guard caught the defect.

## C002 — Correct C-0 oracle semantics

- Trigger: host/worker discrepancy during v2.
- Change: treat zero offset as absolute zero according to the published interpreter.
- Evidence: `tests/test_integrity.py`, preserved interrupted run, final independent audit.
- Result: v2-complete reconciled 7,680 raw generations and 179 training trajectories. No v1 output contained this edge case.
- Limit: agreement on tested examples does not establish universal equivalence.

## C003 — Diagnose distillation regression

- Trigger: search pass@64 moved from 7/24 to 8/24 to 5/24.
- Analysis: `diagnose_distillation.py` writes `analysis/v2-distillation-diagnosis.json` from saved raw outputs.
- Observation: distinct parseable programs per 64 samples fell from 39.75 to 8.46 to 4.58. Round two lost three solved tasks and gained none; round one lost three and gained four.
- Hypothesis: replacing earlier data and repeatedly training on a narrow batch contributed to concentration/forgetting. The observational trajectory does not prove this mechanism.
- Design failure: correct training rows were treated as sufficient for retaining a model update. Search gates did not protect weights.
- Next discriminating test: C004 and C005 with shared frozen trajectories and independent final data.

## C004 — Cumulative verified replay

- Proposal: retain bootstrap and earlier verified task/program pairs; canonical deduplication; independent reverification.
- Control: fresh-round-only training with identical initial checkpoint, optimizer settings, seeds and update opportunities.
- Protocol: `EXPERIMENT-v3-retention.md`, `configs/retention-v3.json`.
- Evidence: `rsi/retention.py`, `tests/test_retention.py`; per-run pools, optimizer events, checkpoints and raw samples.
- Outcome: completed and audited. Replay retained 19.71 distinct parseable programs per task versus fresh-only's 5.08, but final pass@64 was 2/24 versus 3/24. Round-two replay lost two tasks and gained none. See `retention-results-2026-09-16.md`.
- Limit: uniform pair sampling does not guarantee semantic diversity; frozen harvest does not measure recursive improvement.

## C005 — Coverage gate and exact rollback

- Proposal: fresh per-round validation; reject lost solved tasks, pass@64 or pass@1 regression, and ties.
- Control: ungated replay with the same nominal measurement budgets; retain all candidates.
- Evidence: real adapter mutation/restore test; parent/candidate/selected tensor hashes; independent audit.
- Outcome: both live updates passed the 12-task validation slices; the second still regressed on the final bank. Gate and ungated outcomes were identical. Rollback works in the mutation test, but this live experiment did not demonstrate reliable coverage protection.
- Limit: a finite gate cannot guarantee population non-regression. Separate final evaluation never chooses a checkpoint.

## C006 — Explainable experiment records

- Change: timestamped, fsynced hash-chain events; atomic JSON writes; per-step loss, gradient norm, sampled row indices and seed; source/config/bank snapshots; checkpoint lineage; raw validation/final outputs; artifact manifest.
- Verification: 29 tests passed before v3 launch, including rejection despite net coverage gain, task mismatch, invalid replay, old-template exclusion and exact rollback. Two PEFT warnings come from tiny synthetic models lacking pretrained config files.
- Explanation standard: report the intervention and measured effect, then label proposed mechanisms as hypotheses. Preserve rejected and failed attempts.
- Limits: hashes are not signatures; a same-user writer can replace records. Seeds do not guarantee cross-machine GPU replay. Costs distinguish measured tokens/time from logical check bounds.

## C007 — Explain every attempted search edit

- Trigger: old generation records showed only the winning proposal and a table hash, making individual edit attribution cumbersome.
- Change after the sealed v3 experiment: proposal and resolution records for every attempted edit, including operator definition, parent/candidate/selected config hashes, statistics before/after, task IDs, linked evaluation-request hashes, measurements and acceptance/rejection reasons. Non-selected proposals explicitly record that they did not receive admission evaluation.
- Verification: a repeated-operator regression test ensures only the chosen proposal is labeled accepted. Current suite: 30 passing tests. This logging change does not explain or alter the already archived v3 result.

## C008 — Align Kyberos claims with audited research and mission

- Trigger: owner requested frontend/backend review and clarified RSI applications
  as research, cybersecurity, social good and policy. Copy contradicted completed
  pilots and generalized planner replay, verification and release capabilities.
- Change: audited summary exporter, four identical evidence snapshots, negative
  results and four application directions on the frontend, read-only validated
  backend status API, explicit demo/runtime limits and corrected positioning.
- Evidence: `export_kyberos_evidence.py --check` reran both independent audits;
  snapshot `2eea6efde59ba06994cf3dddcdf0da8fe3c510944885ad0f1b4f4daaeba00d13`.
  Backend router 9 tests passed; frontend new UI 2 tests passed, full suite 41
  passed/2 pre-existing ICS failures; build and targeted lint passed. Browser
  checked RSI at desktop/390px and home/demo. Details in Kyberos mission review.
- Result: claims and public evidence now reflect the measured failure to
  demonstrate RSI. No training behavior or experiment outcome changed. Nothing
  was deployed; the existing backend database migration remains separate.
- Limits at this step: standalone router tests do not validate full service
  integration; archived raw results remain local; hashes are not signatures.
  V4 was still an unstarted draft then; C009 records its subsequent completion.

## C009 — Reconstruct inherited statistics and run balanced calibration

- Trigger: v2's 24 source proposals left operator types with 0–4 trials;
  inherited statistics did not outperform controls. Sparse evidence was a
  plausible explanation, not an established cause.
- Change: predeclared v4 collects six trials for each of the 12 existing edits
  per source seed, then transfers g0/g3/g6, scrambled g6 and random selection
  into identical ancestors. No new selection rule or edit vocabulary was added.
- Logging: every evaluation now archives its exact public request and per-batch
  cost delta. Logical charges, oracle upper bounds, worker time and whole-run
  elapsed time have explicit definitions; they are not interchangeable measures.
- Audit: published-interpreter regrading, reconstruction of all effect-table and
  descendant updates, admission decisions, transplanted tables, final lineage,
  optimization cutoff, paired contrasts and compute totals. This independently
  checks decision arithmetic but does not authenticate the host or rerun every
  search. Hash checks alone are not the semantic audit.
- Verification before study: 33 tests passed. Three new tests exercise a real
  small search run and reject altered effect tables and premature final scoring
  even after archive hashes are recomputed. Tiny PEFT fixtures emit two known
  missing-pretrained-config warnings.
- Run: `inheritance-20260916-v4`, completed in 269.55 seconds. Audit passed:
  13,568 search outputs, 736 evaluations and 396 attempts reconciled. g6 averaged
  +0.78 percentage points over g0, +0.26 over g3 and +0.52 over scrambled/random.
  g6−g0 by source: 0.00, +4.69, −2.34 points. This small inconsistent signal does
  not establish reliable inherited improvement or RSI.
- Diagnosis: 193/216 source edits had zero effect. Source 43's same edit had
  negative effects on early slices and positive effects on a later slice at the
  unchanged ancestor; the inherited selector missed that later opportunity.
  Context dependence is observed; a contextual-selector remedy is untested.
- Outcome and decision: `inheritance-results-2026-09-16.md`. Replicate on fresh
  seeds/banks before promoting a selector; isolate any new inference rule in a
  separate comparison. No neural or application-domain result was measured.
- Research: `research-inheritance-update-2026-09-16.md` records the September 14
  RSIAgent paper and the limits of comparisons with HGM and research-process
  improvement. Explicit transferable memory is not a novelty claim.

## C010 — Explain edit selection and replicate before changing the method

- Trigger: v4 had a small mean gain and inconsistent sources. Existing records
  explained candidate outcomes but omitted the random draw and ranking that
  selected the candidate for evaluation.
- Change: optional per-proposal selection trace records available/excluded
  operators, table hash, beta parameters and draws, immediate/descendant terms,
  scores, RNG state hashes, selected name and tie rule. The independent auditor
  reconstructs the stream and arithmetic without calling the selector.
- Behavior gate: new tests compare decisions and RNG state against the archived
  v4 selector for adaptive and random modes, including exclusion exhaustion.
  They also reject a forged draw. Full suite: 36 passed before replication.
- Review tooling: `explain_change.py` renders the choice, parameter diff,
  development/admission wins and losses, costs and statistics. Each report names
  its source hash and journal head, and links evaluations by hash and trajectory
  label. Outputs stay outside sealed archives. Two v4 example reports were
  rendered for an accepted edit and an unselected edit.
- Diagnostic clarification: v4's 193 zero-net-gain trials include two with
  offsetting task wins/losses. All 216 trials contain 26 task wins and 13 losses;
  repeated task-edit observations are not independent samples. This uses existing
  source records only and does not alter the active replication.
- Experiment: `EXPERIMENT-v5-inheritance-replication.md` declares six new source
  seeds, fresh banks and 256 final tasks. Per-source source/transfer budgets and
  selection method are unchanged. No context selector or weight update added.
- Outcome: `inheritance-20260916-v5` completed in 673.09 seconds; audit passed for
  30,976 search outputs and all 792 selection/edit decisions. The replication
  failed its declared screen: g6−g0 −0.1953 points, g6−g3 −0.2604,
  g6−scrambled +0.0651, g6−random −0.3255. Only 1/6 sources beat both empty and
  scrambled (4 required). The current rule is not promoted as a better improver.
- Interpretation: the small v4 benefit did not replicate. Source feedback is
  still sparse (370/432 zero-net proposals). Context dependence, selection-rule
  weakness and edit-space limits remain hypotheses, not established causes.
  Next: grouped source-only effect-prediction tests, then a fresh intervention if
  prediction improves. Details: `inheritance-replication-results-2026-09-16.md`.
- Research update: MetaRSI already reports a common-start improver fork. We no
  longer treat that comparison design alone as a potential novel contribution.
  S3Gym motivates checking transfer separately from local feedback quality.

## C011 — Test context before adding it to the improver

- Trigger: v5 did not replicate inheritance; source effects varied with tasks.
  Missing context was a hypothesis, not an established cause of failure.
- Change: source-only signed-effect prediction using 21 visible-example features
  and eight parent settings. Nested whole-source folds compare zero, mean,
  parent-only, contextual and scrambled-context models. Written exploratory plan
  predates fitting; no transfer/admission/final outcome enters fitting or tuning.
- Logging: source hashes and sanitized row provenance; every fold, nested error,
  permutation, scaling term, coefficient, prediction and menu choice; timestamped
  journal and sealed archive. The independent auditor reconstructs regression
  with a different numerical method and checks partitions and selection.
- Verification: 43 tests passed before fitting, including seven new tests.
  Hidden-field rejection and forgery tests cover predictions, splits and ranking.
- Run: `context-diagnostic-20260916-v6`, completed once. Audit passed 891 fits,
  51,840 predictions and 54 menus. No new search or neural computation.
- Outcome: contextual MSE was 0.658% lower than unconditional means, but ranking
  utility tied parent-only (2.4306 points) and beat means in just 1/9 sources.
  A fixed lexical pair scored 3.1250 points. The declared screen failed; the
  predictor is not installed in the loop. These are offline proposal gains,
  not admitted/final gains. See `context-diagnostic-results-2026-09-16.md`.
- Interpretation: better prediction is not enough. Existing edits had positive
  opportunities in 23/54 menus, but these observations do not prove an edit-space
  ceiling or rule out nonlinear context. Next test a richer verified edit space
  on fresh banks with acquisition controls and the fixed-pair baseline.
- Research: empirical performance models already use instance features and
  algorithm settings. S3Gym motivates checking downstream transfer separately.
  This work makes no new novelty or application-domain success claim.

## C012 — Learn a fragment proposer while resetting the solver for transfer

- Trigger: v6's lower prediction error did not produce reliable edit-selection
  gains. Prior inheritance studies kept the macro library fixed and changed only
  numerical search settings. Missing useful edit opportunities is a hypothesis.
- Change: a dedicated library runner extracts contiguous two-/three-atom
  fragments from oracle-verified harvest solutions, retains certificate links,
  ranks candidates on public examples and tests separate library additions.
  Whole source solutions are verified; their fragments still need change-level
  evaluation. The search implementation and existing numeric selector are unchanged.
- Causal boundary: g0/g3/g6/scrambled proposer memories restart from the identical
  BASE_CONFIG and original active library. Inherited fragments are not installed
  automatically. Numeric-pair and frozen-library controls have the same query
  schedule and source acquisition charge, with actual costs reported separately.
- Logging: memory before/after hashes, every certificate addition, complete
  ranking, source/control construction, all candidates, per-task wins/losses,
  admission reasons, solver/memory snapshots and cost ledgers. A separate readable
  explanation links these records without rerunning search.
- Verification before study: **50 tests passed**, including seven new library
  tests. A real small run reconciles all 84 attempts; tampered memory, ranking
  cost and final-evaluation ordering are rejected even after resealing hashes.
- Protocol: `EXPERIMENT-v7-library.md`, fixed before bank creation; six sources,
  six transfer conditions, six generations and 192 final tasks. Study
  `library-inheritance-20260916-v7` completed in 903.02 seconds and failed its
  screen. All memory arms solved 104/192; g6 trailed the numeric pair by 1.0417
  points on average. Across 293 actual fragment additions, none changed verified
  task correctness and none were installed. Audit reconciled 40,512 outputs and
  all 504 attempts. Full report: `library-results-2026-09-16.md`.
- Limits: fixed fragment-extraction and proposing algorithms; no new edit
  metalanguage, neural training, full RSI claim or application-domain evidence.
  Stitch and recent skill-learning work are relevant prior art. Details:
  `research-library-update-2026-09-16.md`.

## C013 — Reopen cheaper search routes and test the suspected cause

- Trigger: v7 fragments almost never changed the selected program. Inspection
  identified first-arrival duplicate-state suppression as a possible reason.
- Evidence: instrumentation reproduced original outputs and found four cheaper
  routes discarded among all 704 task evaluations for 44 source additions.
  The first 128-task pass included no-ops and found none; both records survive.
- Change: separate `rsi/search_reopen.py` tracks the best cost per state, reopens
  cheaper paths, resets outgoing-edge progress and discards stale queue entries.
  Kernel identity and reopening counts enter its replay-hashed payload. The
  original default worker is preserved for historical protocols.
- Verification: real public-task regression restores a 1.9125 route previously
  suppressed by a 2.55 first arrival; exact replay and primitive-only behavior
  are checked. Full suite: 53 passed, two known PEFT fixture warnings.
- Causal diagnostic: `REOPENING-DIAGNOSTIC-v7.md` fixed the comparison before
  replaying all selected source additions and their corresponding parents under
  the new kernel. `reopening-diagnostic-20260916-v7` saved 70 requests / 1,120
  outputs plus exact replays and passed independent grading/pairing audit.
- Outcome: four states reopened and one selected program changed; zero verified
  correctness changes, zero positive or negative addition effects. This bug does
  not explain those source proposals' zero gains. Neither a fresh trajectory nor
  a new final-bank test of the corrected kernel has run. It is not a demonstrated
  improver-quality gain. Details are in `library-results-2026-09-16.md`.
- Next: inspect all available compatible source fragments at the unchanged
  budget before deciding whether to improve proposal ranking or the edit space.

## C014 — Measure all available single-fragment opportunities

- Trigger: v7 selected 44 source additions with no gain; it was unclear whether
  ranking missed useful remembered fragments.
- Change: enumerate all 60 compatible source-memory additions across 36 fixed
  menus. Sixteen were previously unselected. Keep the corrected reopening kernel,
  original parents and 128-expansion ceiling. No transfer/final/admission query.
- Reuse: 70 request payloads / 1,120 outputs from the audited reopening archive
  match complete request and dependency hashes. Execute the other 26 requests /
  416 outputs with exact replays; report reused and fresh work separately.
- Outcome: `fragment-headroom-20260916-v7`, 9.65 seconds; zero positive or negative
  candidates, zero oracle selection headroom. Independent audit passed all 60
  candidates / 1,536 outputs and cache accounting. This rules out ranking alone
  rescuing those fixed memories/parents/tasks, not all possible libraries.
- Verification: tests reject omitted candidates and changed reused payloads even
  after archive resealing and journal rehashing. Failed directions are retained.
- Next: source-only diagnosis of filtered-space reachability and candidate
  selection. Code inspection found that partially empty pieces were pruned even
  though valid generated programs can require them.

## C015 — Test partially empty pieces and expose the bounded search frontier

- Trigger: the primitive filter incorrectly rejects a piece empty on any visible
  example. A concrete regression task has no visible solution in the old pool
  but is solved by the corrected pool at the same budget.
- Change: isolated partial-empty pool and diagnostic kernel. The original worker
  and historical kernels stay intact. Independently measure visible reachability
  and the cost-ordered unique program frontier; hidden grades arrive after search.
- Verification before measurement: 59 tests passed. Tests check the lost-solution
  case, exact preservation of old pool entries, absence of all-empty additions,
  baseline output identity and deterministic frontier logging.
- Protocol: `PARTIAL-EMPTY-DIAGNOSTIC.md`, frozen before the 576-task measurement.
  Completed in 59.36 seconds: visible reachability 464 -> 576; first-choice
  correctness 357 -> 401; deterministic coverage@64 398 -> 458. First-choice
  wins/losses: 65/21. Primitive charges increased 63.56% at equal ceilings.
- Audit passed 1,152 reexecuted searches, independent visible-reachability checks
  and 17,937 regraded frontier programs. This is a human-directed source-only
  amplifier repair, not neural improvement or RSI. Full report:
  `search-diagnostic-results-2026-09-16.md`.
- Next: prospective fresh-bank cost curves and fixed-total-budget combination;
  then task-balanced frontier distillation with retention controls. Do not
  promote the corrected kernel on retrospective source evidence alone.

## C016 — Prospective search validation and cost curves

- Trigger: C015 improved inspected source tasks but increased actual cost and
  lost 21 previously correct first choices. A retrospective gain cannot promote
  the kernel or establish equal-compute superiority.
- Protocol: `EXPERIMENT-v8-search-validation.md`, frozen before fresh bank
  generation. Six new seeds, 576 tasks, reference-template exclusions from all
  prior protected banks and between groups; budgets 32/64/128/512.
- Compare both filters and a fixed 64+64 mixture, charging both component pools.
  All searches and exact replays close before hidden grading. Record per-call
  CPU/wall times separately from deterministic operation counters.
- Auditing: regenerate banks, rerun search, independently merge and grade
  frontiers, reconstruct paired outcomes and the preregistered screen. Two new
  tests passed before launch, including omission after journal resealing.
- Outcome: `search-validation-20260916-v8` completed in 297.03 seconds and passed
  its screen: joint positive outcomes in 5/6 groups; first choice 332 -> 377/576,
  coverage@64 374 -> 438. There were 62 first-choice wins and 17 losses.
- Costs: corrected@128 used more compute than original@128, but exceeded
  original@512 quality using less measured CPU/wall time and fewer expansions.
  Primitive evaluations remained higher. The fixed mixture gained only three
  first-choice tasks over corrected@128 while paying for both pools.
- Verification: 61 tests passed. Audit regenerated 576 tasks, reexecuted 4,608
  searches, reconstructed 576 mixtures and regraded 66,680 frontier programs.
  Full interpretation: `search-validation-results-2026-09-16.md`.
- Next: versioned corrected-amplifier training arm and task-balanced verified
  frontier distillation, preserving retention and common-ancestor RSI criteria.
- Explanation archive: all 79 changed first choices have old/new programs,
  costs and syntactic-representation checks. All 62 wins used a program outside
  the old pool and followed an empty original result. For 13/17 losses, the old
  correct program reappeared in the corrected frontier at budget 512. Analysis
  code is separately frozen; no new hidden queries or policy selection occurred.
- Literature: September 14 Dream-RSI makes programmable exploration learned
  from historical replay directly relevant prior art. Scope and implications:
  `research-search-validation-2026-09-16.md`.

## C017 — Separate filter, task-coverage and within-task training effects

- Trigger: v8 validated greater verified search coverage, but no neural transfer
  had been measured. Prior distillation lost large-k coverage despite replay.
- Protocol: `EXPERIMENT-v9-frontier-distillation.md`, written before new banks.
  Four arms distinguish original/corrected first choice, first verified frontier
  candidate and all verified candidates. Three training seeds, two rounds.
- Retention: identical initial tensors, cumulative harvest, four anchor and four
  harvested examples per batch, uniform task-then-program draws, and the existing
  admission rule on larger fresh slices. None of these guarantees retention.
- Logging: per-step draws/strata/losses/norms, raw completion token IDs, pinned
  tokenizer reconciliation, sample-cache provenance, every candidate/selected
  tensor hash, gate reasons, exact rollback and final scores deferred until all
  decisions close. Search harvest has separate actual and logical arm charges.
- Verification: 65 tests passed. A first end-to-end fixture failed before bank
  generation because the legacy v2 audit lacks the newer status/manifest schema.
  Preserve `analysis/frontier-v9-verification-fixture/FAILED.json`. Use the sealed,
  audited v3 copy of the same bootstrap, with explicit checkpoint path. The v2
  verification fixture completed in 57.39 seconds; independent audit passed
  136 artifacts, 32 search reexecutions, 1,664 sample checks, 561 verified pool
  rows and all eight optimizer steps/checkpoint decisions. Token counts and
  diversity were independently reconstructed. Its tiny outcomes are not research
  evidence. Full `frontier-distillation-20260916-v9` later failed with CUDA
  memory exhaustion; see C019 for preservation and recovery.
- Full-study harvest closed before training: 117 original first-choice tasks,
  125 corrected first-choice tasks, and 146 corrected-frontier tasks across the
  two rounds. First-verified and full-frontier arms share the same solved task
  sets; the latter contains 1,295 programs. These are training inputs, not neural
  gains. Final results remain deferred. The audit-only report renderer produces
  a readable decision table and per-change provenance/observed-effect JSON.
- Related work and boundaries: `research-frontier-distillation-2026-09-16.md`.

## C018 ? Audit fault tests and evidence-led document revision

- Trigger: hash consistency alone cannot detect a coherently forged archive;
  the brief also lagged completed experiments and over-attributed a published
  pass@k crossover to critic selection.
- Added four tests in `tests/test_frontier_audit.py` against copies of the
  completed GPU fixture. The valid copy passes. Three attacks rebuild journal
  chains and artifact hashes: falsified supervised-token costs, promotion despite
  failed eligibility, and substitution of a final-task reference into training.
- All four tests passed in 27.91 seconds. Each attack was rejected by its intended
  reconstructed semantic invariant, not merely by a stale checksum. These tests
  supplement the earlier 65-test full run; a combined 69-test run is not claimed.
- Limits: these are three concrete fault scenarios. Host-controlled code and
  hashes are not adversarial authentication or proof of exhaustive protection.
- Preserved the original HTML files in `history/pre-v4-20260916/` with hashes.
  Local brief v4 now links measured successes/failures, states the mission,
  separates completed work from hypotheses, and distinguishes deterministic
  coverage from neural pass@k. It corrects the self-training crossover citation
  and requires three H1 controls with separate role adapters.
- Local theory v3 corrects eleven-question counting and H1's partly-covered
  status using scoped ACE evidence. It does not certify the other historical
  gap claims as an exhaustive literature review. `DOCUMENT-STATUS.md` distinguishes
  local revisions, historical narrative/PDF and unchanged published versions.

## C019 ? Preserve a failed neural study and reduce evaluation memory

- Trigger: actual process exit code 1 and `FAILED.json` identify a CUDA allocation
  failure during the fifth candidate's final sampling. Four of 24 update decisions
  closed; five updates/240 optimizer steps finished. Final scoring had not begun.
- Preserved all 104 files of `frontier-distillation-20260916-v9` and recorded an
  external hash inventory in `analysis/frontier-v9-failure-manifest.json`.
  Partial admission outcomes cannot answer the four-arm research question.
- Cause established: GPU out-of-memory. Peak tensors versus fragmentation or
  competing allocations were not distinguished by the available telemetry.
  A short successful fixture did not establish full-run memory reliability.
- Predeclared `EXPERIMENT-v9b-resource-recovery.md`: reduce inference batching
  128 -> 32 for every condition and restart all arms with fresh bank seed 9162610.
  Training, sample counts, decoding parameters and advancement criteria remain
  the same. The failed bank is included in template exclusions. No final scores
  were inspected to choose this recovery. Batching can change sampled outputs;
  this is a separate run, not bit-identical continuation.
- Recovery `frontier-distillation-20260916-v9b` is running. Its harvest contains
  115 baseline first-choice tasks, 126 corrected first-choice tasks and 148
  corrected-frontier tasks across two rounds; the full frontier has 1,423
  verified programs. These are training inputs, not evidence of neural gains.
- Keep repeated/failed work visible as recovery overhead; interrupted sampling
  cost is incompletely recorded. Do not pool partial outcomes or present this
  resource fix as autonomous self-improvement. Audit the completed replacement
  before interpreting it or promoting a policy.
- Reconciled failure accounting: 666 valid chained events, 240 training steps,
  21,572 supervised tokens and 39.54 training seconds; 14 finished sample calls
  recorded 524,554 generated tokens and 870.73 seconds. Interrupted work is
  additional. See `frontier-distillation-failure-2026-09-16.md` and its JSON ledger.
- Added an external, read-only GPU observer without changing frozen code. It
  records device-wide memory/utilization every ten seconds outside the run,
  starting during initial base sampling, and stops when the process exits.
  These samples can miss brief peaks and do not establish an allocator cause.

## C020 ? Re-audit report inputs and define the measurement target

- Trigger: the v9 renderer trusted a historical `audit.json` status and hashed
  three files, while reading additional pool and validation files for change
  explanations. A fabricated pool row could enter a report after the audit.
- Reproduction: a test changed only a copied fixture's training pool. The old
  renderer emitted a report; the expected-rejection test failed. The false
  harvest count was seven rather than six. Historical/new code hashes and the
  observed failure are in `analysis/stale-audit-regression-20260916.json`.
- Repair: require a completed nonfailed study, rerun the independent auditor,
  and verify the entire artifact inventory before audit, after audit and before
  publication. Write reports outside the sealed run. Preserve the audit receipt,
  every evidence hash, auditor version and additional wall/CPU audit cost.
- Verification: five report tests passed in 10.71 seconds. Cases cover valid
  evidence with no trusted old stamp, stale hashes, resealed fabrication, failed
  runs and forbidden output inside the archive. These are targeted tests; no
  new full-suite total is claimed. Live experiment code/protocol hashes match.
- Interpretation: render every declared pass@k column and retain paired seed
  contrasts. Distinguish observed benchmark outcomes, admission reasons and
  untested weight-level explanations. Training seed also changes evaluation
  seed, so differences combine both randomness sources. No additional hypothesis
  tests, confidence intervals, thresholds or checkpoint selections were added.
- Research basis: `research-measurement-reporting-2026-09-16.md`, using NIST AI
  800-3's distinction between fixed-benchmark and population performance. This
  clarification does not make the shared final bank independent across seeds or
  establish mission-domain transfer.
- Scope: the current report path is hardened; other historical renderers have
  not received this same review. Host-owned hashes remain unauthenticated and
  the independent auditor does not reproduce neural training or GPU sampling.
- At v9b completion, invoke `summarize_frontier_distillation.py` once; its fresh
  audit is the publication gate. An additional manual audit immediately before
  it would duplicate the same verification work without resolving a new risk.

## C021 ? Measure descendant-credit support and selection influence

- Trigger: the intended inherited know-how includes descendant productivity,
  but historical source tables contain sparse observations and lineage credit
  is not randomized causal attribution.
- Analysis: freshly audit V5, reconstruct every source/transfer ancestor credit
  and remove score terms while holding recorded draws, alternatives and prior
  choices fixed. Do not execute a hypothetical trajectory or infer unseen edit
  outcomes. `analyze_descendant_credit.py` writes full per-choice/credit records.
- Result: only 9/72 source operator entries had descendant trials, and 5/72 had
  nonzero descendant sums. Removing the descendant term changed 0/432 source
  choices and 2/288 adaptive transfer choices (both source 101, g6 condition).
  The largest absolute descendant score contribution was 0.015625.
- Dependence: source statistics contained 29 ancestor credits from 18 later
  decisions; 15 credits came from rejected candidates and eight involved repeated
  operator names. Transfer added 53 credits from 44 later decisions, 42 from
  rejected candidates. These counts are not independent evidence of causation.
- Verification: the existing independent V5 audit passed again in 4.17 seconds;
  792 recorded proposal choices were analyzed, including 72 random choices for
  which score removal is inapplicable. Three targeted tests passed, covering
  close-choice sensitivity, repeated lineage credit and a forged trial count.
- Limits: beta draws still encode inherited immediate-effect counts. Removing
  only descendant/mean terms is not removal of all inheritance. Later choices
  can diverge after a changed decision. In balanced source calibration all
  twelve edits are evaluated, so proposal ordering alone does not alter that
  generation's candidate set. This is not a prospective ablation result.
- Next discriminating study: separate immediate-only, observational-descendant
  and paired-counterfactual credit under matched acquisition and downstream
  budgets. Distinguish total descendant quality from improvement after the
  initial edit. Requirements are in `NEXT-IMPROVER-CREDIT-STUDY.md`; this is a
  proposed design, not an adopted protocol or claimed new algorithm.
- Evidence: `analysis/descendant-credit-20260916.md` and adjacent JSON; standalone
  analysis source preserved with its recorded hash. No live v9b sources changed.

## C022 - Preregister and audit paired source-credit probe

- Trigger: C021 found that descendant credit is sparse, often assigned to rejected descendants, and rarely changes the recorded selector. A retrospective score ablation cannot estimate what a different initial edit does to later improvement.
- Intervention: preregistered `EXPERIMENT-v10-paired-credit-probe.md` before fresh task generation. Run each of twelve bounded numeric edits and a no-edit baseline from the same source, then give every branch the same two-round downstream proposal schedule, development and admission rules, and measurement bank. Record immediate effect, terminal effect, and the paired change in later improvement separately.
- Scope: six source groups and 72 dependent pairs, using corrected CPU DSL search at expansion ceiling 128. This tests causal headroom in a fixed edit and downstream-policy space. It does not train an inherited selector, improve model weights, or establish RSI.
- Implementation evidence: a separate 10-task fixture closed 13 branches and 12 pairs. Its independent auditor passed 42 hashed artifacts, 486 journal events, 278 unique searches and exact replays, 312 regraded task rows, and all 12 effects. Five focused tests passed, including resealed fabricated effects and premature measurement that the auditor rejected. Fixture outcomes are implementation checks, not research findings.
- Full run `runs/paired-credit-20260916-v10` completed and its independent audit passed: 42 hashed artifacts, 9,760 journal events, 288 regenerated tasks, 7,376 unique searches and exact replays, 8,736 regraded task rows, 78 reconstructed branches and 72 recomputed effects.
- Result: later-improvement effects were positive in 8/72 pairs, negative in 2/72 and zero in 62/72; nonzero pairs occurred in four of six source groups. The declared nonzero headroom screen passed, but this sparse signal does not establish that a learned selector can predict or use it. Immediate effects had 16 positive, 18 negative and 38 zero pairs; terminal effects had 21 positive, 17 negative and 34 zero pairs. Pairs within a source group share tasks and a no-edit branch, so 72 is not an independent replication count.
- Cost: 7,376 physical searches plus 7,376 exact replays, 1,463,652 charged expansions, 112,913,306 charged primitive executions, 401.45 search/replay wall seconds and 445.56 runner elapsed seconds, excluding the later independent audit. The v9b neural study overlapped the run, so wall time may reflect contention.
- Next decision: design a prospective immediate-only versus observational-credit versus paired-credit inheritance comparison at matched acquisition and downstream compute. The source probe supports an estimable target within this narrow edit space, not a promoted memory policy or RSI.

## C023 - Stop V9b neural reporting at an oracle/auditor semantics mismatch

- Trigger: all 24 neural update decisions closed, but the report renderer's fresh independent audit stopped while checking `distinct_visible_behaviors`, before it could publish a report. The runner's declared advancement screen was false; because the audit failed, do not treat that screen or detailed scores as verified research results.
- Reproduction: saved `s17_base` output on final task `54458378e7930858bfa5` includes `Concat(upper(Sub(M(WORD,1,start),M(WORD,1,End))))`. The published DSL parser/interpreter treats `End` as end for a match side other than `start`, yielding `['ZOE', 'PRIYA', 'ZOE']` on the visible strings. The independent AST oracle requires lowercase `end` and yields `[None, None, None]`. The reported diversity metric uses the independent oracle; the auditor reconstructed it with the published interpreter, so the asserted counts diverge.
- Characterization: 198,656 saved sample outputs had 172,879 published/oracle incorrect pairs, 25,774 correct/correct pairs, and 3 oracle-only accepted outputs. No published-only correct outputs occurred. There were 106 visible-output vector disagreements; two contained uppercase `End`. The three oracle-only cases used trailing commas accepted by Python AST but rejected by the published parser. Full details are in `analysis/v9b-semantic-mismatch-20260916.md` and JSON.
- Decision: the canonical generated DSL grammar is the contract. The strict oracle now rejects trailing commas before closing parentheses, with regression tests for trailing commas and uppercase `End`. Keep the V9b archive frozen and its neural result unverified; do not patch the audited run or silently change its scores.
- Next: snapshot the repaired oracle/auditor in a new protocol, regenerate excluded tasks, rerun the controlled neural study, and require a fresh independent audit before promoting pass@k or admission results. This is a benchmark-contract repair, not model or improver improvement.

## Remaining RSI work

## C026 - Prepare V12 credit-mode transfer controls

- Trigger: V10 passed the source headroom check, while V11 showed that a richer verified frontier did not improve the neural transfer pipeline. The next discriminating question is whether paired later-improvement credit helps the bounded improver choose edits on fresh tasks.
- Implementation: `operators.select` and `evolution.evolve` now support explicit `immediate_only`, `observational_descendant`, and `paired_credit` score fields without changing the legacy default. `credit_transfer.py` converts the audited V10 rows into separate frozen tables and creates a scrambled paired control. Three focused tests cover field separation, paired-mode selection and scrambling.
- Protocol: `EXPERIMENT-v12-credit-transfer.md` and `configs/credit-transfer-v12.json` freeze six source groups, six conditions, equal downstream opportunities, V10 evidence cost accounting, fresh-bank exclusions and the final screen. The runner/auditor launch remains outstanding; no V12 task bank has been generated.
- Verification: full suite passed 141 tests after the selector change. The implementation fixture was resealed to current source hashes.
- Historical boundary: V11's audit receipt passed before V12 selector source changes. Do not rerun V11 against the mutable live tree and call a source-hash failure a V11 result; use its sealed source snapshot and saved audit receipt.
- Next decision: implement and fixture-test the V12 runner/auditor, then generate the fresh bank and launch only after the archive/replay gates pass.

## C029 - Evolve the improver's own AST-ranking policy

- Trigger: V66 synthesized new AST substrates but still used a fixed candidate-ranking policy. V67 tests whether the improver can mutate and retain its own selection policy under a held-out admission gate.
- Intervention: evolve a population of scoring genomes over candidate AST features, select on development, require admission non-regression against the frozen V66 scorer, then evaluate the retained genome on a fresh final bank.
- Result: across two fresh seeds, evolved scoring improved final from 15/24 to 18/24 and from 17/24 to 22/24. It improved development/admission from 19/24 to 23/24 and 15/24 to 20/24 on seed 41, and from 19/24 to 21/24 and 16/24 to 18/24 on seed 42. The evolved policy was selected twice.
- Verification: both independent audits passed, replaying 216 rows and checking 19 sealed artifacts per run. Evidence is in `analysis/meta-ast-v67-results.md` and `runs/meta-ast-v67-20261001` / `runs/meta-ast-v67-20261002`.
- Limits: the mutation operators, feature vocabulary, AST primitives, oracle-labeled selector protocol, and synthetic domain remain authored. This is policy-level recursive improvement, not open-ended RSI.
- Next: evolve grammar and architecture mutations with compute matching, neural priors, and held-out mechanism families, so the retained object changes the proposer’s substrate as well as its ranking.

## C030 - Evolve the improver's executable AST grammar architecture

- Trigger: V67 improved the AST proposer's ranking policy, but did not change which typed operators or complexity levels were available. V68 tests whether an evolved grammar mask and structural ranking mode can improve transfer.
- Intervention: evolve enabled AST operators, maximum expression complexity, and ranking mode on development; require admission non-regression against the frozen V67 scorer; evaluate the retained architecture on fresh final banks.
- Result: across two seeds, evolved and frozen matched on development, admission, and final (12/24, 17/24, 18/24 on seed 43; 21/24, 19/24, 16/24 on seed 44). The admission gate retained frozen on both seeds.
- Verification: both independent audits passed, replaying 144 rows and checking 18 sealed artifacts per run. Evidence is in `analysis/meta-grammar-v68-results.md` and `runs/meta-grammar-v68-20261003` / `runs/meta-grammar-v68-20261004`.
- Limits: the superset grammar, operator vocabulary, mutation operators, visible supervision, and synthetic affine domain remain authored; this is a boundary result, not evidence that open-ended architecture evolution has been solved.
- Next: evolve constructor/constant grammar or failure-driven operator invention and evaluate on a mechanism family absent from the mutation catalog, with a compute-matched gate.

## C031 - Respond to representation failure with typed constructor invention

- Trigger: V68 showed that mutating an existing AST operator mask did not improve transfer. V69 tests whether the improver can open a new constructor layer when the legacy ordinal grammar has no visible solution.
- Intervention: activate generic bit-count, parity, rotate-left, and gcd constructors only after a visible legacy failure; evolve the retained constructor subset on development; require admission non-regression against broad invention; evaluate on hidden popcount, rotation, and gcd mechanisms.
- Result: across two fresh seeds, legacy scored 5/24 and 9/24 final, while broad and evolved invention scored 15/24 and 19/24. Evolution selected only `popcount` on both seeds and passed admission twice.
- Verification: both independent audits passed, replaying 216 rows and checking 19 sealed artifacts per run. Evidence is in `analysis/failure-invention-v69-results.md` and `runs/failure-invention-v69-20261005` / `runs/failure-invention-v69-20261006`.
- Limits: constructor templates, mutation operators, visible target alignment, and synthetic task mechanisms remain authored; this is bounded failure-driven recursive improvement, not open-ended RSI.
- Next: evolve short typed stack programs from a lower-level instruction set and test on a mechanism absent from the instruction templates and mutation catalog.

## C032 - Rediscover the useful representation in a lower-level stack language

- Trigger: V69 improved transfer by selecting the named `popcount` constructor. V70 tests whether that representation can be reconstructed without named popcount, rotation, or gcd primitives.
- Intervention: after legacy failure, search a typed stack language of loads, constants, shifts, bitwise operations, arithmetic, modulo, and generic bit-fold map/reduce; evolve retention between fold and bit-mix families; require admission non-regression.
- Result: across two seeds, legacy scored 13/24 and 9/24 final, while broad and evolved stack discovery scored 24/24 final on both. The evolved architecture selected only `fold` on both seeds and reached 24/24 on development and admission.
- Verification: both independent audits passed, replaying 216 rows and checking 19 sealed artifacts per run. Evidence is in `analysis/stack-discovery-v70-results.md` and `runs/stack-discovery-v70-20261007` / `runs/stack-discovery-v70-20261008`.
- Limits: the stack instruction set, generic fold primitive, mutations, visible alignment, and synthetic mechanism family remain authored; this is bounded compositional RSI evidence, not open-ended RSI.
- Next: remove `fold_bits` and evolve its reduction from raw shifts, masks, and arithmetic instructions against a new reduction family.

## C033 - Remove the generic fold instruction

- Trigger: V70 reached 24/24 after supplying a generic `fold_bits` abstraction. V71 tests whether the representation survives when that abstraction is removed.
- Intervention: construct reductions explicitly from repeated loads, single-bit masks, shifts, XOR/add reducers, modulo, and raw shift/or bit mixing; evolve retention between raw bit-reduce and bitmix families with held-out admission.
- Result: across two seeds, legacy scored 0/24 final on both, while broad and evolved raw synthesis scored 19/24 and 21/24. Evolved selection matched broad synthesis and passed admission twice.
- Verification: both independent audits passed, replaying 216 rows and checking 20 sealed artifacts per run. Evidence is in `analysis/raw-stack-v71-results.md` and `runs/raw-stack-v71-20261009` / `runs/raw-stack-v71-20261010`.
- Limits: raw instruction vocabulary, template enumeration, mutations, visible alignment, and synthetic mechanisms remain authored; this is partial bounded RSI evidence, not open-ended RSI.
- Next: mutate raw instruction sequences with counterexample-guided grow/delete/splice operations, without predeclared reduction-family templates.

## C034 - Evolve raw programs through counterexample-guided mutation

- Trigger: V71 still enumerated two researcher-defined raw program families. V72 tests whether executable programs can be built by grow/delete/splice mutation over generic typed instruction fragments.
- Intervention: after legacy failure, evolve fragment sets and reducers from visible behavior signatures; expose only the resulting executable programs; evolve the retained term budget and ranking policy; require admission non-regression.
- Result: across two seeds, legacy scored 0/24 final on both, while broad and evolved mutation scored 19/24 and 21/24. The evolved policy selected an eight-term budget on both seeds and passed admission twice.
- Verification: both independent audits passed, replaying 216 rows and checking 20 sealed artifacts per run. Evidence is in `analysis/mutation-stack-v72-results.md` and `runs/mutation-stack-v72-20261011` / `runs/mutation-stack-v72-20261012`.
- Limits: instruction vocabulary, fragment grammar, mutation operators, visible alignment, and synthetic mechanisms remain authored; this is partial bounded RSI evidence, not open-ended RSI.
- Next: allow the mutation engine to alter its own fragment grammar and instruction vocabulary under a protected sandbox and held-out instruction family.

## C035 - Evolve the executable instruction grammar

- Trigger: V72 still fixed the primitive instruction vocabulary and mutation grammar. V73 tests whether the improver can edit which executable instructions are available and retain a compact grammar under held-out admission.
- Intervention: expose a safe sandbox containing dormant unary/bitwise operations; annotate candidate programs with required instruction sets; evolve enabled operations, complexity, and ranking on development; require admission non-regression.
- Result: across two regenerated seeds, legacy scored 12/24 and 5/24 final, while broad and evolved grammars scored 18/24 and 13/24. The evolved grammar converged to `and`, `mod`, `not`, `shr`, `xor` on both seeds.
- Verification: both regenerated independent audits passed, replaying 216 rows and checking 20 sealed artifacts per run. Evidence is in `analysis/self-editing-grammar-v73-results.md` and `runs/self-editing-grammar-v73-20261015` / `runs/self-editing-grammar-v73-20261016`.
- Contract repair: the earlier exploratory V73 archives were excluded after a test caught a masking-order mismatch between candidate semantics and hidden-domain generation; fresh archives were generated after repair.
- Limits: sandbox semantics, grammar mutation operators, visible alignment, and synthetic mechanisms remain authored; this is bounded grammar-level RSI evidence, not open-ended RSI.
- Next: synthesize and validate new macros/instruction definitions from existing primitives, then test on a mechanism absent from both initial grammar and mutation catalog.

## C036 - Retain mined executable macros across tasks

- Trigger: V73 evolved a compact executable grammar but regenerated the representation separately for each task. V74 tests whether successful visible-only programs can be normalized into reusable macros and replayed on later tasks.
- Intervention: mine parameterized stack bodies from development visible examples only; deduplicate and retain a bounded macro library; add macro execution to the evaluator; compare legacy, direct grammar, and mined-macro arms under held-out admission.
- Result: the library retained 3 macros and generated 144 macro candidates across 72 evaluation tasks. Legacy scored 8/24 final, while direct grammar and mined macro both scored 24/24; mined macro passed admission and was selected. The result shows transfer and compression, not an accuracy gain over direct synthesis.
- Verification: independent audit passed, replaying 216 arm-task rows and checking 22 sealed artifacts. Evidence is in `analysis/macro-invention-v74-results.md` and `runs/macro-invention-v74-20261019`.
- Limits: stack vocabulary, normalization, candidate grammar, visible alignment, admission gate, and synthetic mechanism family remain researcher-authored; this is one fresh seed and bounded abstraction retention, not open-ended RSI.
- Next: replicate across unrelated mechanism families, require the macro library to transfer out of family, and test whether retained macros can be composed or modified to create genuinely new behavior.

## C037 - Transfer retained macros across a family boundary

- Trigger: V74 showed visible-only macro retention within the same synthetic family. V75 tests whether the retained representation remains useful when development uses `macro_transition` but admission/final use `novel_operator_transition`.
- Intervention: construct explicit cross-family banks, mine macros from development visible examples only, and compare legacy ordinal, direct stack grammar, and mined-macro replay across two fresh seeds.
- Result: mined macros matched direct grammar on both cross-family replications: final 13/24 and 19/24 versus legacy 7/24 and 11/24. The mined arm passed admission and was selected twice; each library contained 3 macros.
- Verification: both independent audits passed, replaying 216 arm-task rows and checking 20 sealed artifacts per run. Evidence is in `analysis/cross-family-macro-v75-results.md` and `runs/cross-family-macro-v75-20261021` / `runs/cross-family-macro-v75-20261022`.
- Limits: the family boundary, low-level code-point structure, macro grammar, task generator, visible alignment, and admission gate remain researcher-authored; this is replicated bounded transfer, not open-ended RSI.
- Next: evolve or compose retained macros under a protected mutation budget, with the proposal mechanism itself held out from the initial grammar.

## C038 - Test compositional self-improvement of retained macros

- Trigger: V75 showed cross-family macro transfer but no accuracy advantage over direct synthesis. V76 tests whether retained macros can compose into new behavior.
- Intervention: add ordered macro-pair composition with six arithmetic/bitwise combinators and bounded outer moduli; compare legacy, direct grammar, replayed macros, and composed mutation on the V75 cross-family protocol.
- Result: composed mutation matched direct/replayed performance at 16/24 and 11/24 final across two seeds, while legacy scored 8/24 and 6/24. It generated 188 and 162 candidates but was never selected.
- Verification: both independent audits passed, replaying 288 arm-task rows and checking 22 sealed artifacts per run. Evidence is in `analysis/composed-macro-v76-results.md` and `runs/composed-macro-v76-20260923` / `runs/composed-macro-v76-20260924`.
- Limits: the combinator language only combines existing outputs; it cannot yet edit internal bodies or introduce new stack instructions. Bounds, family design, visible alignment, and admission remain authored.
- Next: evolve typed instruction sequences themselves—allow safe body edits, new stack operators, and counterexample-guided proposals—then test whether the representation can create a genuinely novel operator.

## C039 - Introduce typed internal body invention

- Trigger: V76 showed that output-level macro composition did not expand behavior. V77 exposes low-level serialized stack fragments, including shift/or bit mixing, to test instruction-level invention.
- Intervention: add a typed body-editor arm using visible-only bit-reduction and bitmix proposals, while retaining legacy, direct grammar, and mined-macro controls on the same cross-family protocol.
- Result: across two seeds, the body editor matched direct/replayed final performance at 20/24 and 19/24, versus legacy 7/24 and 8/24. It passed admission twice but was never selected over mined macros.
- Verification: both independent audits passed, replaying 288 arm-task rows and checking 23 sealed artifacts per run. Evidence is in `analysis/typed-body-editor-v77-results.md` and `runs/typed-body-editor-v77-20260925` / `runs/typed-body-editor-v77-20260926`.
- Limits: the current editor is a bounded typed proposer with macro provenance, not yet true parent-body grow/delete/splice mutation; instruction vocabulary, fragments, visible alignment, and admission remain authored.
- Next: implement actual self-editing of serialized macro bodies, retain edits only after held-out admission, and test whether an edited body transfers to a mechanism absent from the seed library.

## C040 - Mutate retained bodies with parent protection as the next target

- Trigger: V77 exposed low-level body proposals but did not edit retained code. V78 directly mutates retained bodies through typed constant/operator edits and balanced raw-bit grafts.
- Intervention: start from each mined macro body, enumerate bounded internal edits, and select visible-separator candidates; compare against protected unmodified macro replay and direct grammar on two cross-family seeds.
- Result: internal mutation matched legacy at 2/24 and 8/24 final, while direct/replayed macros scored 9/24 and 16/24. It was ineligible and never selected in either replication.
- Verification: both independent audits passed, replaying 288 arm-task rows and checking 22 sealed artifacts per run. Evidence is in `analysis/internal-body-mutation-v78-results.md` and `runs/internal-body-mutation-v78-20260927` / `runs/internal-body-mutation-v78-20260928`.
- Limits: one mutation generation, authored edit vocabulary, no lineage credit, no protected-parent rollback, and researcher-authored admission remain. The null shows naive mutability is destructive, not that self-improvement is impossible.
- Next: add lineage-level counterexample credit, immutable parent archives, multi-generation mutation, and admission-gated rollback so edits can only replace a parent after demonstrating held-out improvement.

## C041 - Preserve parents while accumulating edited descendants

- Trigger: V78 showed that direct macro-body mutation can destroy transfer performance. V79 tests immutable-parent lineage retention with bounded descendant accumulation.
- Intervention: mine three parent macros, generate visible-consistent typed children on development tasks, retain parents permanently, freeze the 15-body descendant library, and compare it with unmodified replay and unprotected mutation on held-out family tasks.
- Result: lineage matched the protected macro baseline at 13/24 and 16/24 final across two seeds and avoided unprotected mutation collapse to 6/24 and 7/24. The lineage grew from 3 to 15 bodies in both runs.
- Verification: both independent audits passed, replaying 360 arm-task rows and checking 25 sealed artifacts per run. Evidence is in `analysis/lineage-macro-v79-results.md` and `runs/lineage-macro-v79-20260929` / `runs/lineage-macro-v79-20260930`.
- Limits: no lineage credit assignment or admission-gated replacement yet; mutation language, caps, family design, and visible retention remain authored.
- Next: evolve children across multiple generations, assign counterexample-based cross-task credit, and replace a parent only when a child improves held-out admission while preserving prior tasks.

## C042 - Add cross-task lineage credit

- Trigger: V79 showed that immutable-parent accumulation preserves transfer but does not improve it. V80 requires mutated children to earn support from multiple independent development tasks across two generations.
- Intervention: retain a child only when at least two development tasks support its visible behavior; keep all parents immutable; compare credit lineage with replay and unprotected mutation on the held-out family.
- Result: the credit lineage expanded 3 parents to 12 bodies on both seeds, matched replay at 19/24 and 14/24 final, and passed admission twice. Unprotected mutation scored 12/24 and 7/24.
- Verification: both independent audits passed, replaying 360 arm-task rows and checking 25 sealed artifacts per run. Evidence is in `analysis/credit-lineage-v80-results.md` and `runs/credit-lineage-v80-20261001` / `runs/credit-lineage-v80-20261002`.
- Limits: credit preserves but does not yet improve the substrate; proposal grammar, support threshold, caps, family design, and gate remain authored.
- Next: add counterexample-guided novelty pressure, lineage diversity, and admission-gated parent replacement so a supported child can earn a real performance advantage.

## C043 - Reserve mutation budget for internal grafts

- Trigger: V80 showed that cross-task credit stabilizes lineage but does not expand behavior. V81 reserves one-third of the mutation budget for stack-balanced raw-bit grafts.
- Intervention: version the mutation neighborhood behind `reserve_grafts=True`, preserve historical replay defaults, and run the V80 lineage protocol with the new graft budget.
- Result: the lineage grew from 3 to 15 bodies but scored 11/24 final versus direct grammar 12/24; one right-shift/or graft entered the library and the reserved-graft arm was not selected.
- Verification: independent audit passed, replaying 360 arm-task rows and checking 26 sealed artifacts. Evidence is in `analysis/reserved-graft-lineage-v81-results.md` and `runs/reserved-graft-lineage-v81-20261003`.
- Limits: one seed; the graft is one-sided and cannot express the balanced rotation operator implicated by the held-out family. Mutation vocabulary, support rule, and admission remain authored.
- Next: add a typed two-branch rotate graft, then test parent protection, lineage credit, and held-out retention separately.

## C044 - Invent and transfer a balanced rotate operator

- Trigger: V81 showed one-sided grafts could not express the held-out rotated mechanism. V82 adds a balanced masked left/right shift branch as a typed mutation from an identity seed.
- Intervention: learn on visible `novel_operator_transition` tasks, require two-task support, retain immutable parents, and transfer the frozen lineage to `stack_transition` tasks with the matching `bit_splice` operator.
- Result: the lineage retained five bodies and solved all matching `bit_splice` tasks (6/6 and 8/8) with no false positives on other stack mechanisms. Direct grammar still scored 24/24 overall and was selected.
- Verification: both independent audits passed, replaying 360 arm-task rows and checking 28 sealed artifacts per run. Evidence is in `analysis/rotate-lineage-v82-results.md` and `runs/rotate-lineage-v82-20261006` / `runs/rotate-lineage-v82-20261007`.
- Limits: rotate mutation, family relation, support rule, operator bounds, and admission remain authored; this is selective bounded operator invention, not open-ended RSI.
- Next: remove the named rotate mutation, evolve branch structure from generic typed fragments, and evaluate against several unrelated operators with matched direct-synthesis controls.

## C045 - Remove the named rotate mutation with generic typed-body evolution

- Trigger: C044 showed selective rotate transfer but still relied on an authored rotate mutation.
- Intervention: V83 assembled stack bodies bottom-up from generic typed leaves and binary operators, required two-task support, retained immutable parents, and replayed the frozen lineage on a separate stack family.
- Result: generic evolution and generic lineage matched legacy overall (10/24 final) but solved all 10/10 `bit_splice` tasks and zero other stack mechanisms; a fresh MAP-Elites bank replicated the selective result at 7/7, with 7/24 overall versus direct 24/24.
- Verification: both independent audits passed, each replaying 288 arm-task rows and checking 24 sealed artifacts. Evidence is in `analysis/generic-body-evolution-v83-results.md`, `runs/generic-body-evolution-v83-20261008`, and `runs/generic-body-evolution-v83-mapelites-20261009`.
- Limits: the generic grammar and support gate remain authored, and selective behavior does not prove that the retained body is the intended rotate representation or establish open-ended RSI.
- Next: scale generic composition to deeper branch structures with an explicit compute-matched control and inspect transfer across multiple unrelated operators.

## C046 - Replicate generic transfer with structural MAP-Elites niches

- Trigger: V83's aggregate null masked a selective `bit_splice` transfer signal.
- Intervention: preserve full operator-signature niches rather than only visible-behavior beam elites, using the same immutable lineage and cross-family replay protocol.
- Result: on a fresh bank, generic lineage solved 7/7 `bit_splice` tasks and 0/17 other mechanisms; overall final was 7/24 versus direct grammar 24/24.
- Verification: the independent audit passed, replaying 288 arm-task rows and checking 24 sealed artifacts. Evidence is in `analysis/generic-body-evolution-v83-results.md` and `runs/generic-body-evolution-v83-mapelites-20261009`.
- Limits: maximum body size was seven nodes, so the archive could not express the full balanced two-branch rotate body; the selective result may be a functional shortcut.
- Next: scale generic composition to deeper branch structures with an explicit compute-matched control and inspect whether retained bodies transfer across multiple unrelated operators.

## C047 - Add factorized hierarchical generic composition

- Trigger: V83's seven-node search transferred `bit_splice` selectively but could not test whether the retained body was a deeper multi-branch reconstruction.
- Intervention: factor generic typed search into a subexpression library and balanced pair composition, reaching 11-node bodies without naming rotate, bitmix, or another target operator.
- Result: the four-task pilot reached the deeper search space, but no child met the two-task support threshold; final scores were legacy 2/4, direct 4/4, generic 2/4, and lineage 2/4.
- Verification: the independent audit passed, replaying 48 arm-task rows and checking 24 sealed artifacts. Evidence is in `analysis/hierarchical-body-v84-pilot-results.md` and `runs/generic-body-evolution-v84-hierarchical-pilot-20261011`.
- Limits: the pilot is underpowered for transfer claims; a full bank is required, with substantial compute cost.
- Next: run the hierarchical mode on a full fresh bank with compute-matched direct and non-hierarchical controls.

## C048 - Compare full-bank hierarchical and flat generic body search

- Trigger: V84's pilot showed that deeper composition was reachable but was underpowered for transfer inference.
- Intervention: build one frozen development-only global body bank and compare hierarchical factorization against flat search at the same 11-node and 64-state limits, with identical lineage credit and held-out replay.
- Result: both generic arms solved 12/12 `bit_splice` tasks and zero other mechanisms, scoring 12/24 final versus direct grammar 24/24. Hierarchical retained 20 bodies versus flat 17 but did not improve accuracy.
- Verification: both independent audits passed, each replaying 288 arm-task rows and checking 25 sealed artifacts. Evidence is in `analysis/hierarchical-global-v84-results.md`, `runs/generic-body-evolution-v84-hierarchical-global-20261013`, and `runs/generic-body-evolution-v84-flat-global-20261013`.
- Limits: selective transfer may be a functional shortcut caused by shared code-point structure; no claim of semantic rotate reconstruction or open-ended RSI is made.
- Next: break the shared low-level convention with unrelated encodings and use adversarial counterfactual tasks to test whether the retained body represents an operator rather than a correlated predicate.

## C049 - Break the shared code-point convention with adversarial encoding

- Trigger: V84's flat and hierarchical lineages both solved all held-out `bit_splice` tasks only while development and evaluation shared a low-level code-point convention.
- Intervention: add visible-only task encodings (`identity`, `xor55`, `affine5`, `rotate3`) and run a compute-matched V85 global-body experiment with identity development and `xor55` admission/final encoding.
- Result: generic lineage fell to 8/24 final and solved 0/11 `bit_splice` tasks, versus 12/12 bit-splice transfer in both V84 matched-encoding controls. Direct grammar scored 13/24 and was selected; it also solved 0/11 encoded bit-splice tasks.
- Verification: the independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Evidence is in `analysis/adversarial-encoding-v85-results.md` and `runs/generic-body-evolution-v85-encoding-xor55-20261017`.
- Limits: one adversarial seed and one XOR encoding are insufficient for a general representation-invariance claim; encoding inference remains absent and the task generator/search language are authored.
- Next: replicate across affine and rotation encodings, then give the improver an explicit representation-learning/encoding-inference substrate and test whether it can retain an encoding-invariant operator rather than a raw predicate.

## C050 - Add bounded representation-hypothesis adaptation

- Trigger: V85 eliminated generic lineage's prior selective bit-splice transfer under `xor55` held-out encoding.
- Intervention: add an encoding-aware stack primitive and an adaptive lineage arm that tests identity, XOR, affine, and rotate representations against visible examples after lineage retention.
- Result: adaptive lineage recovered 11/11 final bit-splice tasks and scored 19/24 overall, versus plain lineage 0/11 bit-splice and 8/24 overall. It passed admission at 19/24 but was not selected because development-first ranking favored direct grammar (18/24 development versus adaptive 8/24).
- Verification: the independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Evidence is in `analysis/encoding-adaptation-v86-results.md` and `runs/generic-body-evolution-v86-encoding-adaptive-20261017`.
- Limits: the representation catalog and selection rule are authored; one adversarial bank was used, and the adaptive arm has extra hypothesis-search cost.
- Next: evolve the representation hypothesis prior and admission-aware selector, then replicate across affine and rotation shifts with matched candidate-search budgets.

## C051 - Test admission-first selection of representation adaptation

- Trigger: V86 recovered encoded bit-splice transfer but the development-first selector rejected the adaptive lineage arm.
- Intervention: rank admission-eligible arms by admission correctness, then development correctness, and evaluate on a fresh encoded bank.
- Result: the adaptive arm was selected prospectively at 17/24 admission versus direct grammar 12/24, solved 9/9 final bit-splice tasks, but scored 13/24 final versus direct grammar 15/24. Across V86–V87 it recovered 20/20 encoded bit-splice tasks, while overall final results were mixed (19/24 and 13/24 versus direct 13/24 and 15/24).
- Verification: the independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Evidence is in `analysis/admission-selector-v87-results.md` and `runs/generic-body-evolution-v87-admission-selector-20261017`.
- Limits: two seeds and one held-out encoding do not establish a robust selector; admission distribution, encoding hypotheses, and search costs remain authored.
- Next: use risk-aware multi-objective selection that preserves direct-grammar coverage while adding adaptive specialists, and replicate across affine5 and rotate3 shifts.

## C052 - Compose direct grammar with an adaptive specialist portfolio

- Trigger: V87 selected adaptive lineage correctly for the shifted family but regressed aggregate final accuracy from 15/24 to 13/24.
- Intervention: select the shortest visible-compatible candidate per task from direct grammar plus encoding-adaptive lineage, retaining the existing admission gate and development-first architecture ranking.
- Result: on a fresh third bank, specialist portfolio was selected, passed 24/24 admission, and reached 24/24 final versus direct grammar 17/24 and adaptive lineage 15/24; it solved all 7/7 encoded bit-splice tasks.
- Verification: the independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Evidence is in `analysis/specialist-portfolio-v88-results.md` and `runs/generic-body-evolution-v88-specialist-portfolio-20261017`.
- Limits: one prospective seed; extra candidate-generation cost; representation catalog and portfolio ranking remain authored.
- Next: replicate portfolio selection under affine5 and rotate3, then match candidate-search budgets and test whether a learned reliability model can replace the hand-authored shortest-compatible rule.

## C053 - Replicate specialist portfolio under affine encoding

- Trigger: V88 showed 24/24 final under xor55 but was only one encoding family.
- Intervention: keep the portfolio and adaptive hypothesis set fixed while changing held-out encoding to affine5 on a fresh bank.
- Result: the portfolio was selected and improved final accuracy from 0/24 direct grammar to 10/24, recovering 10/10 bit-splice tasks but 0/14 fold tasks.
- Verification: the independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Evidence is in `analysis/specialist-portfolio-v89-affine5-results.md` and `runs/generic-body-evolution-v89-specialist-portfolio-affine5-20261017`.
- Limits: one affine seed; transfer is selective and the adaptive catalog/search cost is extra.
- Next: test rotate3, then evolve a learned reliability/portfolio policy rather than relying on shortest visible-compatible candidates.

## C054 - Replicate specialist portfolio under rotation encoding

- Trigger: V89 showed selective affine transfer and left open whether the portfolio survives a bit permutation.
- Intervention: keep the V88/V89 portfolio and adaptive hypothesis set fixed while changing held-out encoding to rotate3 on a fresh bank.
- Result: portfolio was selected and reached 24/24 final, matching direct grammar; it solved 7/7 bit-splice, 10/10 fold-parity, and 7/7 fold-mod3 tasks. Across XOR, affine5, and rotate3, it recovered 28/28 available bit-splice tasks.
- Verification: the independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Evidence is in `analysis/specialist-portfolio-v90-rotate3-results.md` and `runs/generic-body-evolution-v90-specialist-portfolio-rotate3-20261017`.
- Limits: one rotation seed, authored encoding catalog, extra adaptive search cost, and no unseen-encoding extrapolation.
- Next: evaluate a held-out encoding not present in the hypothesis catalog and replace the hand-authored portfolio rule with a learned reliability model under matched compute.

## C028 - Replace the fixed primitive catalog with a self-describing AST proposer

- Trigger: V65 expanded the language but still hard-coded transform families and constants. V66 tests whether a generic typed AST search can synthesize the needed primitive composition without a named family catalog.
- Intervention: enumerate arithmetic ASTs, deduplicate by observed behavior signatures, retain low-complexity alternatives, and compare the AST proposer with the prior ordinal and V65 catalogs on a fresh affine-fold bank.
- Result: across two fresh seeds, the AST proposer scored 19/24 and 22/24 final and was selected twice. Baseline, universal ordinal, and V65 primitive-catalog controls scored 0/24 final on both seeds.
- Verification: both independent audits passed, replaying 288 rows and checking 25 sealed artifacts per run. Evidence is in `analysis/ast-proposer-v66-results.md` and `runs/ast-v66-20260929` / `runs/ast-v66-20260930`.
- Limits: AST operations, constant bounds, retention policy, novelty/coherence priors, visible supervision, and synthetic mechanisms remain authored. This is substrate synthesis inside a bounded meta-language, not open-ended RSI.
- Next: evolve the proposer’s grammar, cost model, and retention policy themselves, with held-out admission and cross-family replication.

## C027 - Expand the executable language with failure-driven transforms

- Trigger: V64 created compound expressions but still lacked floor-division, Gray-code, and multi-bit-field transforms. V65 tests whether a failure-driven extension layer can add these primitives and transfer to hidden transform families.
- Intervention: generate typed transform atoms for quotient-periodic rules, shifted/XOR bits, and masked fields; compose them through the same semantic solver. Add a visible-only coherence prior requiring a run’s start and end to reuse one predicate.
- Result: across two fresh seeds, primitive invention scored 20/24 development, 20/24 admission, and 20/24 final on both seeds and was selected twice. V64 expression scored 6/24 and 5/24 final; the previous ordinal grammar scored 0/24 on both.
- Verification: both independent audits passed, replaying 432 rows and checking 24 sealed artifacts per run. Evidence is in `analysis/primitive-invention-v65-results.md` and `runs/primitive-v65-20260927` / `runs/primitive-v65-20260928`.
- Limits: the transform catalog, constants, coherence prior, supervision, and synthetic task generator remain researcher-authored. The result is bounded primitive expansion, not open-ended RSI.
- Next: replace the fixed transform catalog with a learned/grammar-guided AST proposer trained on failure signatures, and require held-out admission plus replication before retaining a new primitive.

## C026 - Synthesize compound operators inside a typed grammar

- Trigger: V63 unified modular and bitwise families, but the substrate still could not express a compound rule. V64 tests whether typed program composition can create a new executable operator family rather than select a named family arm.
- Intervention: search one generic ordinal expression language with arithmetic atoms, comparisons, boolean composition, and behavior-signature indexing. Use a fresh mixed hidden-symbol bank containing modulus, bit, threshold, and OR-of-arithmetic mechanisms with no family labels.
- Result: across two fresh seeds, the generic expression grammar scored 24/24 development, admission, and final on both seeds and was selected twice. The prior universal ordinal grammar scored 17/24 and 20/24 final; baseline and reflective controls scored 0/24; char-set controls scored 3/24 and 7/24.
- Verification: both independent audits passed, replaying 360 rows and checking 23 sealed artifacts per run. Evidence is in `analysis/compositional-expression-v64-results.md` and `runs/expression-v64-20260924` / `runs/expression-v64-20260925`.
- Limits: all primitive operators, span composition, visible target alignment, complexity bounds, and the synthetic mechanism generator remain researcher-authored. This is compositional bounded synthesis, not open-ended RSI.
- Next: make primitive-function proposals themselves a learned or evolved object, selected on held-out mechanisms, and measure whether later generations expand the primitive vocabulary without a named operator catalog.

## C025 - Unify arithmetic-family invention under one grammar

- Trigger: V62 showed that a bitwise family could be synthesized, but its separate family arm was still researcher-authored. V63 tests whether the solver can choose between hidden modular and bitwise mechanisms inside one shared ordinal grammar.
- Intervention: combine divisor-derived modular predicates and bit-position predicates into one universal candidate generator. Evaluate a mixed hidden-symbol bank whose tasks randomly use `ord % 11` or bit 3, without exposing the family label. Retain reflective and memorized-character controls.
- Result: across two fresh seeds, baseline, reflective, and `char_set` controls scored 0/24 final each; the universal grammar scored 24/24 final on both seeds, and also 24/24 on both development and admission splits. The universal arm was selected twice.
- Verification: both independent auditors passed, replaying 288 rows and checking 22 sealed artifacts per run. Results are in `analysis/universal-v63-results.md` and the two `runs/universal-v63-*` archives.
- Limits: the grammar still contains researcher-authored ordinal constructors; visible target alignment, span composition, candidate budget, and the synthetic mixed-task generator remain fixed. This demonstrates bounded mechanism inference, not open-ended RSI.
- Next: synthesize the arithmetic grammar itself from smaller primitives and evaluate against held-out mechanism families whose names and constructors are absent from the runner.

## C024 - Launch V11 after the DSL contract repair

- Trigger: C023 found 106 visible-behavior disagreements and three oracle-only accepted trailing-comma programs in V9b's saved samples. The root cause was a mismatch between the canonical generated grammar, strict oracle and permissive auditor interpreter.
- Repair: strict oracle rejects trailing commas; frontier audit and score reconciliation now use the strict oracle for correctness and visible-behavior diversity. The implementation fixture was resealed to the new source hashes. Full suite: 84 tests passed.
- Protocol: `EXPERIMENT-v11-frontier-contract-repair.md`, new bank seed 9162612, same four arms/training seeds/settings as V9b, all prior protected-bank templates excluded. The V9b archive is frozen and never pooled.
- Status: `runs/frontier-distillation-20260916-v11` completed. Its source snapshot includes the repaired oracle and auditor. The independent audit and report-time audit passed.
- Result: the declared screen failed. Corrected-frontier minus corrected-selected selected-round-two pass@64 was -0.52 percentage points, positive in 1/3 seeds, and below frozen bootstrap. Corrected-first-verified reached 22.40% mean pass@64, while corrected-frontier reached 20.31%; this does not establish an improved model or improver.
- Next decision: preserve V11 as a negative transfer result, update the flagship report, and design the prospective immediate-only versus observational-credit versus paired-credit inheritance comparison at matched acquisition and downstream compute. Do not select a checkpoint retrospectively.

## C025 - Validate V11 and save the negative result

- Trigger: V11 completed after the V9b contract repair and required its independent audit before interpretation.
- Verification: audit passed 310 artifacts, 1,718 journal events, 320 regenerated tasks, 384 reexecuted/replayed harvest searches, 221,184 raw samples, 10,122 training rows, 1,152 optimizer steps and 24 checkpoint decisions. A second report-time audit also passed.
- Screen: failed 3 of 5 criteria. Primary delta was -0.0052083, with one positive seed. Full report: `frontier-distillation-results-2026-09-17.md`; checkpoint: `STATUS-2026-09-17.md`.
- Limits: training and GPU sampling were not replayed; seeds share bank/bootstrap; costs are not fully matched; finite-example oracle and local hashes do not prove all-input correctness or hostile-host integrity.

Evidence-density audit of v2 (`analysis/v2-improver-evidence-density.json`): each source seed tested only 24 proposals across 12 operator types. Individual operators had 0–4 trials; source seeds 17/29/43 had 4/0/2 beneficial proposals and 2/0/2 accepted edits. Sparse evidence is another plausible reason the inherited table failed. Test a better-calibrated effect-estimation experiment before attributing failure solely to missing context. No causal mechanism is established by these counts.

Replicate retention findings across neural seeds and larger banks; reconnect the selected policy to interleaved search; separately test parent regularization; improve contextual edit statistics and richer operators; rerun common-ancestor and inheritance controls; match total compute. Novelty remains unconfirmed. C004–C006 do not satisfy these requirements by themselves.


## C046 - Test the recommended trio and expose interface mismatch

- V67/V72/V73 were run on one fresh shared `mutation_transition` pilot bank with equal small budgets. The audit passed.
- V67 solved 2/8 final tasks; V72 and V73 solved 0/8. The bank was outside the native target assumptions of the latter two arms, so the pilot is an interface smoke test and not a ranking result.
- Before stitching ten versions, define a common candidate envelope, mixed-family bank, shared admission gate, and leave-one-arm-out controls. See `EXPERIMENT-stitch-ten.md`.

## C047 - Run the ten-component integration pilot

- Intervention: wrap V65/V67/V69/V70/V72/V73/V75/V77/V80 semantic proposal generators in one visible-only candidate envelope and development/admission source-priority router. Test V8 on its own DSL task lane. Preserve a source-drift failure and rerun on two fresh banks.
- Result: the semantic router scored 10/12 twice, against best native scores 8/12 and 7/12. Random-priority scores were 3/12 and 6/12. V8 scored 9/12 versus original 5/12, then tied 8/12. Both completed independent audits replayed 324 candidate-generation calls and 24 DSL searches each.
- Limit: the router acquired all nine semantic candidate pools and took about 177/162 seconds, so the native comparison is not equal compute. Only V67 and V73 supplied complementary final programs; the V8 DSL is separate. No recursive policy evolution or mission-domain evaluation is demonstrated.
- Next: compare a minimal V67+V73 router with native/direct controls at matched compute across at least six fresh groups. Evidence: `STITCH-TEN-PILOT-RESULTS-2026-09-17.md`.
