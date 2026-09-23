# System-level RSI proposal: literature and design check

Status note added after implementation: the proposal below was subsequently adopted and tested on 2026-09-16. Its original recommendation text is preserved as historical reasoning. The controlled pilot did not meet RSI criteria; see `pilot-results-2026-09-16.md`. The retention follow-up and current evidence are tracked in `CHANGE-REGISTER.md`.

16 September 2026. This is a targeted primary-source review, not an exhaustive priority claim. The GATS-based proposal remains **not yet adopted**. The result of the review is that its components have close prior art; the testable contribution is a particular causal comparison of inherited improvement knowledge inside a verified search-and-distill loop.

## Closest work

Later update, after v4: [MetaRSI-v1](https://arxiv.org/html/2609.06396v1)
section 5.4 explicitly compares original and updated improvers from the same
starting system. Treat it as a direct comparator; the common-start test itself
is not a novelty claim. See `research-inheritance-update-2026-09-16.md` for the
sections inspected and verification limits.

| Work | Overlap | Consequence for our claim |
| --- | --- | --- |
| [Expert Iteration](https://arxiv.org/abs/1705.08439), [ReST-EM](https://arxiv.org/abs/2312.06585) | Search or generation supplies better examples; a learner absorbs them; the cycle repeats. | Amplify → distill is established. |
| [SOAR](https://arxiv.org/html/2507.14172) (2025; revised March 2026) | Evolutionary program search alternates with hindsight learning that improves the model's sampling and refinement operators. It reports gains over iterations and a matched-compute comparison against more base-model search. | **The closest direct comparator.** Search → program solutions → improved search model is not new. Compare inherited edit knowledge and self-created edit types against SOAR-style fixed sampling/refinement. |
| [STOP](https://arxiv.org/abs/2310.02304), [Darwin Gödel Machine](https://arxiv.org/html/2505.22954), [Recursive Harness Self-Improvement](https://arxiv.org/html/2607.15524) | A scaffold, agent codebase, or harness is iteratively changed and evaluated while the underlying model can remain fixed. DGM notes its archive exploration rule is fixed. | Editing an amplifier is established. Changing the *rule that proposes and selects edits* remains a sharper target than changing task prompts or solution code. |
| [Huxley Gödel Machine](https://arxiv.org/html/2510.21614) | Defines clade metaproductivity, aggregates descendant outcomes into a per-agent estimate, and uses Thompson sampling to guide expansion. Reports transfer of a discovered agent across tasks and model backbones. | Distinguishing artifact fitness from capacity to improve is **already explicit prior art**. Do not claim descendant statistics or transfer are new. The possible distinction is an **operator-conditioned, portable table** whose causal value is tested by copying and scrambling it while holding the executable improver fixed. |
| [Gödel Agent](https://arxiv.org/html/2410.04444), [ADAS](https://arxiv.org/html/2408.08435) | Agent logic and building blocks can be written and revised by a model; ADAS searches code-defined agents and transfers discovered designs. | Self-created edit types are not novel by themselves. A persistent, validated edit catalog with measured downstream contribution might be distinct. |
| [AlphaEvolve](https://arxiv.org/abs/2506.13131) | Evolutionary code search with automated evaluators for scientific and algorithmic problems. | Verified program search and evaluator feedback are established. |
| [SPADE](https://arxiv.org/abs/2608.19197), [SelfMem](https://arxiv.org/abs/2607.03726) | Adaptive environment design and self-optimized agent memory, respectively. | Dynamic task selection and memory adaptation are nearby, not stand-alone novelty claims. |
| [2606.07856](https://arxiv.org/html/2606.07856) | Teacher-free, exact-verifier string DSL on Qwen3-4B; a learned critic selects candidates at inference, while its STaR training loop uses verifier-filtered generator outputs. Trained generator wins at pass@8 and loses to base at pass@64 across four training trajectories. | Excellent local negative baseline, but its observed crossover is an empirical result in one domain, not a theorem that sampling can never expand support. |

The [DGM objective-hacking example](https://arxiv.org/html/2505.22954) changed tool-use logging so its evaluator missed hallucinated tool calls. This motivates putting the authoritative oracle and event capture outside the editable component. “Fitness it cannot fake” is too absolute: the claim must name the write boundary, process boundary, oracle inputs, and residual attacks. Bit-exact replay checks reproducibility and unauthorized changes; it does not prove a proposed program generalizes.

## Narrow hypothesis worth testing

> On a frozen, independently scored task distribution and matched total compute, a system that inherits a verified, operator-conditioned model of edit effects yields more future improvement than the same executable amplifier with an empty or scrambled effect table. When allowed to add validated edit operators, it beats the same system restricted to the initial operator catalog. Search-generated, oracle-verified trajectories then improve the generator's **raw** large-k pass@k beyond the self-training baseline.

This is a **combination and causal evaluation hypothesis**, not an established novelty claim. The literature checked here did not show this exact table-transfer intervention in the same small-model program-synthesis loop. A broader search is still needed before claiming priority.

### Four outcomes to keep separate

1. **Solver coverage:** raw independent samples from each generator checkpoint, judged by the hidden oracle. Report pass@1 and pass@k through at least 64, with paired tasks and uncertainty intervals. Do not mix this with search or selection.
2. **Amplifier ability:** solve rate versus an equal *inference* budget using the same frozen generator and same allowed visible examples. Compare generations 0, 3, and 6 after resetting task-specific journals. This measures improvements to search, not weights.
3. **Inherited improvement knowledge:** freeze the executable amplifier and macro library; transplant only the effect table into a fresh run. Compare intact, empty, and scrambled tables across matched future edit and evaluation budgets. If macros or operator definitions are also inherited, test them in separate factorial cells.
4. **Ability to improve the improver:** apply each generation's editing process to the same frozen amplifier ancestor and fresh tasks. Compare the distribution of descendant gains after a fixed number of proposed edits and oracle calls. This is the direct HGM-style metaproductivity test, with a common ancestor to avoid attributing a better starting artifact to a better editing rule.

For new edit types, count both creation cost and later reuse. Attribute a gain to an edit type only with an ablation that removes that type and reruns selection under the same budget. A raw “share of gains” from accepted edits is selected on success and does not establish causality.

## Experimental design corrections

- Pre-register **two primary curves**: raw generator pass@k after each distillation and amplified solve@budget before it. The first tests learned coverage; the second tests system-level search. A search win over raw base pass@64 is not, on its own, a weight-level coverage win.
- Compare against the published self-training setup, a frozen amplifier, a SOAR-style fixed sample/refine amplifier with trace distillation, a fixed-prompt local meta-improver, random gated edits, and (as an optional stronger ceiling) fixed-prompt Opus. Count training, generation, oracle calls, replay, and failed edits separately. A fixed Opus run is not compute-matched to Qwen merely by equal call count.
- Split tasks by underlying generated program/template as well as by examples. Keep the hidden oracle and its inputs outside the editable process. Limit visible feedback so repeated attempts cannot reconstruct the holdout. Maintain a separate final bank never used for edit admission or table updates.
- Define replay as a deterministic check of saved inputs, outputs, versions, seeds, and oracle judgments. Admission additionally requires independent held-out improvement and no proxy/oracle discrepancy beyond a predeclared threshold. Record discrepancies as incidents; reject the candidate while investigating them.
- Specify an operational large-k frontier with finite budget, not “programs the base never produces at any k.” A finite negative sample cannot establish zero probability. The domain ceiling and task prior can also make improvement plateau without proving the method lacks broader potential.
- Use multiple independent *training* seeds, not only evaluation split seeds. Lock the final holdout, pass@k grid, generations, compute ledger, stopping rule, and success threshold before observing outcomes.

## Starting substrate and engineering reality

The [paper's public repository](https://github.com/izzortsi/trapdoor-loom) includes `dsl.py`, task-generation code, `banks/`, training/evaluation scripts, and result artifacts. Its README describes frozen 200-task easy and hard banks, Qwen3-4B-Instruct-2507, NF4 QLoRA, and an RTX 3090. The repo has a `banks/` directory; confirm exact contents, license, hashes, and reproducibility locally before using those banks as a final holdout. Since the public banks and reported results are visible, a fresh independently generated final bank is preferable for the new claim.

The local `C:\Users\reese\gats\gats2` implementation has MCTS, progressive widening, a transposition table, and action verification. Its current `LLMProposer` proposes names from a predefined `valid_actions` list and defaults to `gpt-4o-mini`; the executor applies action-model inventory effects. It does **not** yet synthesize string DSL programs with a pinned local Qwen model. The first implementation milestone is a DSL state/action adapter plus local-model proposer and oracle boundary, then a frozen-amplifier baseline. Calling the existing code “GATS search for DSL solutions” would otherwise overstate readiness.

## Decision after the audit

Recommend **the system-level loop as the flagship hypothesis**, with H1 nested as a later edit-operator study. Start with a reproduction of the June paper's base and self-training curves, then a fixed GATS-style amplifier against SOAR-style sample/refine, then effect-table inheritance. Introduce self-created edit types only after the fixed catalog and oracle boundary work. This sequence makes a failure interpretable at each stage. The proposal remains unadopted until the research direction is chosen.

The literature check covered the named papers and the additionally important SOAR, RHI, and SelfMem. It does not establish that no other work has the same transplant/scramble design; search that exact intervention again immediately before publication.
