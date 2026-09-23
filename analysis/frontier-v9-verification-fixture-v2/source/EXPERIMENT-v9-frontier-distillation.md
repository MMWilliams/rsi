# V9: verified-frontier distillation with retention and causal controls

Written before generating new banks or observing their outcomes. This follows
v8's validated amplifier repair. It tests transfer into a pinned local model,
not recursive improver quality or a reproduction of the 4B reference paper.

## Frozen conditions

Model: Qwen3-0.6B revision c1899de289a04d12100db370d81485cdf75e47ca, bfloat16 base,
rank-8 q/v LoRA with identical float32 adapters. Start every arm/seed from the
audited v2 common-bootstrap adapter, using its sealed, audited v3 copy. Also measure the unadapted base and frozen
bootstrap on the same new final bank. Training seeds 17, 29, 43; two rounds.

Generate fresh harvest_round1=96, harvest_round2=96, validation_round1=32,
validation_round2=32, final=64 tasks with bank seed 9162609. Three visible and
thirteen hidden examples, max four atoms; exclude all prior protected-bank
reference templates and keep new splits template-disjoint. Preserve the 46
original verified bootstrap tasks as a separate anchor stratum. Hidden examples
of harvest tasks can certify training targets; validation/final targets cannot
enter training. Search receives only IDs and visible examples.

Both search filters use frozen BASE_CONFIG, the v7 common macros and ceiling
128. Exact replay every harvest task under each filter and retain its first
64 unique cost-ordered candidates. Grade after search, using both interpreters.
Harvest is fixed before neural training and shared across seeds; its costs are
reported once and as per-arm logical acquisition costs, not silently free.

Four arms, each with its own independently restored checkpoint:

1. **baseline_selected**: original filter's first candidate, only if verified.
2. **corrected_selected**: corrected filter's first candidate, only if verified.
3. **corrected_first_verified**: first verified candidate in corrected frontier.
4. **corrected_frontier**: all distinct verified programs in corrected frontier.

Contrasts 2−1 isolate the filter's effect on this training pipeline; 3−2 test
additional solved training tasks; 4−3 test multiple programs for the same solved
tasks. Keep task weighting identical between arms 3 and 4. This does not isolate
all semantic diversity from syntactic multiplicity.

## Training and retention

Each update uses AdamW, learning rate 0.0002, 48 steps, batch size 8, norm clip
1.0, completion-only cross entropy, max encoded length 1024 with no truncation.
Every batch draws exactly four anchor and four cumulative harvested examples.
Within each stratum draw a task uniformly, then a program uniformly. Keep round
one harvest available in round two. Separate RNG streams for anchor-task,
harvest-task and program choices prevent program counts changing anchor draws.
If no verified harvest is available, skip the update and record it explicitly.

This fixed anchor fraction is a common retention intervention across all arms,
not a separately validated cure for v3's coverage regression. No parent-policy
regularizer or on-policy distillation is added. Optimizer steps/examples match;
tokens, search costs and total compute can differ and must be reported.

Sample 64 raw programs per task for each parent/candidate on that round's
32-task admission bank. Retain a candidate only if it loses no previously solved
admission task, does not reduce pass@1 or pass@64, and strictly improves at least
one of those aggregate measures. This is the existing finite-sample gate, not
a guarantee of true retention. Restore rejected adapters with exact tensor hash
verification; retain candidate and selected checkpoint artifacts and reasons.

Save candidate outputs on the 64-task final bank, but defer all final scoring
until every optimization decision is closed. Evaluate initial, unadapted base,
every candidate and each arm's selected round checkpoints. Same generation seed
per training seed across final checkpoints. Parent-admission samples may be
reused only with an exact checkpoint/request/config key and explicit provenance.

## Measures and advancement screen

Report raw neural pass@1/4/8/16/32/64, per-task counts, syntactic diversity and
visible-behavior diversity. Never relabel deterministic search coverage as neural
pass@k. Report final gains/losses after each decision, including admission false
acceptances/rejections as observed on the separate final bank. No final feedback
may change a checkpoint or threshold.

Primary contrast: corrected_frontier versus corrected_selected, selected round
two pass@64. Advance the frontier policy only if this mean difference is positive,
it is positive in at least two of three training seeds, and corrected_frontier's
selected round-two mean pass@64 is above both frozen bootstrap and unadapted base
and no lower than its selected round-one mean. All four conditions are required.
The first-verified arm explains whether any benefit is task coverage or multiple
programs. Report candidates even if a restrictive gate yields tied selected arms.
This engineering screen neither establishes statistical significance nor RSI.

No threshold changes or final-selected checkpoints after seeing outcomes.
Three seeds still provide limited uncertainty about training variability; the
bank is shared, so task-seed observations are not independent task draws.

## Evidence and boundaries

Snapshot code/protocol/config before bank generation. Journal provenance,
requests, exact search replay, every frontier grade and certificate, data-stratum
membership, all optimizer draws/losses/gradient norms/tokens, checkpoint tensor
hashes, raw generation requests/outputs/costs, admission decisions and rollback.
Archive failures and never overwrite a run ID. GPU seeds do not promise identical
training across hardware/software. Oracle checks cover finite examples, not all
inputs; host-owned hashes are not authentication against the host.

An auditor reconstructs banks and harvest arms, regrades samples with the
published interpreter, reconciles every draw with its task-balanced distribution,
checks exact checkpoint lineage, admission decisions, final sample reuse and the
screen. Neural training is not replayed by the audit. Acquisition, training,
generation, oracle, replay and audit costs remain separate. No deployment or
application-domain capability is implied.
