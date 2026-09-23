# RSI research project

Mission: **RSI for research, cybersecurity, social good and policy**.

Research notes, executable experiments, and artifacts for *The Münchhausen Machine* and the related self-improvement loop study.

## Working prototype

The system-level proposal was adopted for implementation on 16 September 2026. The prototype combines bounded DSL search, independent oracle checks, deterministic replay, an inherited operator-effect table, model-proposed edit expressions, and verified local Qwen LoRA distillation.

**[Completed pilot results](pilot-results-2026-09-16.md):** the loop runs and its integrity checks pass. The first controlled test does not demonstrate RSI: large-k coverage regresses after the second distillation, and inherited effect tables do not beat their controls.

- [Architecture and setup](ARCHITECTURE.md)
- [Gap coverage and remaining limits](GAP-COVERAGE.md)
- [Pilot protocol](EXPERIMENT.md)
- [Calibrated v2 protocol](EXPERIMENT-v2.md)
- [Run history and fixes](RUN-HISTORY.md)
- [Change-by-change evidence and explanations](CHANGE-REGISTER.md)
- [Retention experiment v3](EXPERIMENT-v3-retention.md)
- [Retention results: greater variety, no sustained coverage gain](retention-results-2026-09-16.md)
- [Recent retention research and design decisions](research-retention-2026-09-16.md)
- [September RSI criteria and remaining tests](research-rsi-update-2026-09-16.md)
- [Inherited fragment results and cheaper-route diagnosis](library-results-2026-09-16.md)
- [Search-filter diagnosis: improved source coverage with costs and regressions](search-diagnostic-results-2026-09-16.md)
- [Prospective fresh-task search validation protocol](EXPERIMENT-v8-search-validation.md)
- [Fresh validation results: coverage gain replicated, costs and regressions remain](search-validation-results-2026-09-16.md)
- [Latest search-policy literature check](research-search-validation-2026-09-16.md)
- [Verified-frontier distillation protocol](EXPERIMENT-v9-frontier-distillation.md)
- [V9 GPU failure and fresh recovery protocol](EXPERIMENT-v9b-resource-recovery.md)
- [Audited V11 frontier report](analysis/frontier-distillation-v11-report.md)
- [V12 compute-matched multi-seed protocol](EXPERIMENT-v12-compute-matched-multiseed.md)
- [V13 framework sweep and findings program](EXPERIMENT-v13-framework-sweep.md)
- [Current structured findings ledger](analysis/findings-ledger.json)
- [V13 meta-search exploratory result](analysis/meta-search-v13-20260917.md)
- [V13 evolved-policy result and replication](analysis/policy-evolution-v13-results.md)
- [V13 contextual policy selector result](analysis/contextual-policy-v13-results.md)
- [V13 audited neural micro-loop result](analysis/neural-micro-v13-results.md)
- [V14 replay-and-gate neural result](analysis/neural-gated-v14-results.md)
- [V15 open-ended operator lab](analysis/open-ended-v15-results.md)
- [V16 neural-symbolic hybrid result](analysis/hybrid-v16-results.md)
- [V17 search-kernel controller result](analysis/kernel-controller-v17-results.md)
- [V18 neural fragment-macro hybrid result](analysis/fragment-hybrid-v18-results.md)
- [V19 neural-seeded CEGIS result and replication](analysis/cegis-v19-results.md)
- [V20 visible-constant synthesis result](analysis/cegis-v20-results.md)
- [V21 admission-gated architecture evolution result](analysis/architecture-evolution-v21-results.md)
- [V22 AutoML architecture search result](analysis/automl-architecture-v22-results.md)
- [V23 active counterexample-guided synthesis result](analysis/active-cegis-v23-results.md)
- [V24 retained synthesis-prior null](analysis/meta-prior-v24-results.md)
- [V25 generator-derived Bayesian prior gain](analysis/bayesian-prior-v25-results.md)
- [V26 exact library-learning null](analysis/library-learning-v26-results.md)
- [V27 anti-unified library result](analysis/antiunification-v27-results.md)
- [V28 active epsilon-retention null](analysis/epsilon-retention-v28-results.md)
- [V29 hierarchical Bayesian shape prior](analysis/shape-prior-v29-results.md)
- [V30 audited shape-prior beta sweep null](analysis/shape-beta-sweep-v30-results.md)
- [V31 audited tabular RL query-controller negative result](analysis/rl-query-v31-results.md)
- [V32 audited structural confidence-gate replication](analysis/confidence-query-v32-results.md)
- [V33 audited relational anti-unification null](analysis/relational-prior-v33-results.md)
- [V34 audited evolutionary ranking-program null](analysis/genetic-ranker-v34-results.md)
- [V35 audited verified macro-compression signal](analysis/compressed-macro-v35-results.md)
- [V37 audited active-trajectory macro induction](analysis/active-macro-v37-results.md)
- [V38 audited deeper active macro compression](analysis/active-macro-v38-results.md)
- [V39 audited MDL/BPE macro grammar null](analysis/bpe-macro-v39-results.md)
- [V40 audited episodic retrieval signal](analysis/retrieval-macro-v40-results.md)
- [V41 audited retrieval/shape ablation](analysis/retrieval-ablation-v41-results.md)
- [V42 audited recursive macro composition](analysis/recursive-macro-v42-results.md)
- [V43 audited bounded operator-invention attribution](analysis/operator-invention-v43-results.md)
- [V44 audited adaptive search-width controller](analysis/adaptive-width-v44-results.md)
- [V45 audited adversarial curriculum attribution](analysis/adversarial-curriculum-v45-results.md)
- [V46/V47 audited depth-shift pressure tests](analysis/depth-shift-v46-v47-results.md)
- [V48 audited quality-diversity recursive learning](analysis/diverse-recursive-v48-results.md)
- [V49 audited recursive-library consensus ensemble](analysis/ensemble-recursive-v49-results.md)
- [V50 audited shifted semantic operator transfer](analysis/semantic-domain-v50-results.md)
- [V51 audited generic boundary-span induction](analysis/generic-span-v51-results.md)
- [V52 audited cross-domain generic-span transfer](analysis/cross-domain-v52-results.md)
- [V53 audited run-predicate boundary transfer](analysis/runpredicate-v53-results.md)
- [V54 audited induced structural predicate transfer](analysis/induced-signature-v54-results.md)
- [V55 audited raw ordinal-range predicate transfer](analysis/ordrange-v55-results.md)
- [V56 audited disjoint-alphabet representation selection](analysis/representation-selection-v56-results.md)
- [V57 audited generated feature-language selection](analysis/feature-language-v57-results.md)
- [V58 audited reflective primitive discovery](analysis/reflective-v58-results.md)
- [V59 audited online predicate invention](analysis/online-invention-v59-results.md)
- [V60 audited extrapolative operator invention](analysis/extrapolative-v60-results.md)
- [V61 audited unbounded arithmetic invention](analysis/unbounded-arithmetic-v61-results.md)
- [V62 audited arithmetic-family discovery](analysis/bitwise-v62-results.md)
- [V63 audited universal ordinal grammar](analysis/universal-v63-results.md)
- [V64 audited compositional expression synthesis](analysis/compositional-expression-v64-results.md)
- [V65 audited failure-driven primitive invention](analysis/primitive-invention-v65-results.md)
- [V66 audited self-describing AST proposer](analysis/ast-proposer-v66-results.md)
- [V67 audited meta-evolution of the AST proposer](analysis/meta-ast-v67-results.md)
- [V68 audited meta-evolution of the AST grammar architecture](analysis/meta-grammar-v68-results.md)
- [V69 audited failure-driven typed constructor invention](analysis/failure-invention-v69-results.md)
- [V70 audited lower-level typed stack-program discovery](analysis/stack-discovery-v70-results.md)
- [V71 audited raw-instruction stack discovery](analysis/raw-stack-v71-results.md)
- [V72 audited counterexample-guided stack mutation](analysis/mutation-stack-v72-results.md)
- [V73 audited self-editing executable grammar](analysis/self-editing-grammar-v73-results.md)
- [V74 audited visible-only macro invention and cross-task replay](analysis/macro-invention-v74-results.md)
- [V75 audited cross-family macro replay](analysis/cross-family-macro-v75-results.md)
- [V76 audited compositional macro mutation](analysis/composed-macro-v76-results.md)
- [V77 audited typed internal body invention](analysis/typed-body-editor-v77-results.md)
- [V78 audited internal mutation of retained bodies](analysis/internal-body-mutation-v78-results.md)
- [V79 audited immutable-parent lineage retention](analysis/lineage-macro-v79-results.md)
- [V80 audited cross-task lineage credit](analysis/credit-lineage-v80-results.md)
- [V81 audited reserved-budget graft lineage](analysis/reserved-graft-lineage-v81-results.md)
- [V82 audited balanced rotate-operator invention](analysis/rotate-lineage-v82-results.md)
- [V83 audited generic typed-body evolution and selective transfer](analysis/generic-body-evolution-v83-results.md)
- [V84 hierarchical generic-body pilot](analysis/hierarchical-body-v84-pilot-results.md)
- [V84 full-bank hierarchical versus flat generic transfer](analysis/hierarchical-global-v84-results.md)
- [V85 adversarial code-point encoding](analysis/adversarial-encoding-v85-results.md)
- [V86 bounded representation adaptation](analysis/encoding-adaptation-v86-results.md)
- [V87 admission-first architecture selection](analysis/admission-selector-v87-results.md)
- [V88 specialist portfolio under representation shift](analysis/specialist-portfolio-v88-results.md)
- [V89 specialist portfolio under affine encoding](analysis/specialist-portfolio-v89-affine5-results.md)
- [V90 specialist portfolio under rotation encoding](analysis/specialist-portfolio-v90-rotate3-results.md)
- [Failure report and recorded recovery costs](frontier-distillation-failure-2026-09-16.md)
- [Frontier-training literature and causal controls](research-frontier-distillation-2026-09-16.md)
- [Measurement targets and report-integrity update](research-measurement-reporting-2026-09-16.md)
- [Pilot configuration](configs/pilot.json)
- `rsi/` — implementation; `tests/` — oracle, boundary, replay, and measurement checks.
- `runs/<run-id>/` — raw results, source snapshots, journals and audit records;
  narrative reports are linked above or in the run history. `runs/latest.json`
  refers to the original pilot family; later studies have separate pointers.
- `requirements.lock.txt` — installed environment versions; `vendor/trapdoor-loom/` retains upstream Git provenance.

Run the calibrated CPU pilot with `.\.venv\Scripts\python.exe -m rsi.run --config configs/pilot-v2.json`; add `--neural` for the pinned local Qwen experiment on GPU 1. See the architecture document for environment and model setup. Model-created edits use a fixed bounded expression language. The pilot tests implementation and component effects; it does not establish RSI or optimality.

## Documents

The local brief v4 and gap register v3 include targeted September updates and links to measured evidence. Narrative/PDF, close readings and published pages retain their earlier versions. See [document status](DOCUMENT-STATUS.md) for scope and provenance. Experimental outcomes are maintained in the reports and change register.

- `munchhausen-machine.html` — local technical brief v4: measured evidence, active system experiment, and three-arm H1 follow-up.
- `munchhausen-machine-long.html` — original narrative version.
- `The-Munchhausen-Machine.pdf` — PDF of the narrative version.
- `print.html` — print source used for the PDF.
- `twenty-loops.html` — close readings of twenty papers.
- `load-bearing-theory.html` — local gap update v3: eleven questions, corrected H1 status; other entries retain their earlier review scope.
- `gap-audit-2026-09-16.md` — updated prior-art check, experiment-design corrections, and research priorities.
- `flagship-literature-check-2026-09-16.md` — system-level comparison, including SOAR and HGM, and the inherited-improver hypothesis.

The textbook PDFs remain in `C:\Users\reese\Documents\rsi-library`.

## Published pages

- [Technical brief, v3](https://claude.ai/artifact/TGoQu9gcaUo7v6Y1nqonpC)
- [Twenty papers, v2](https://claude.ai/artifact/XGHgetMMA5ApxeTrAerVzx)
- [Theory and gap register, v2](https://claude.ai/artifact/Ap9nNyFFjbChcHQ34HZG8d)

Next actions are tracked in `.claude/TODO.md`.
