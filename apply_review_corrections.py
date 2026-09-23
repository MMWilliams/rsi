"""Apply the accepted corrections from the 2026-09-21 external reviews.

Each replacement asserts its target text exists so a silent no-op is impossible.
Run once; it refuses to run twice.
"""
from __future__ import annotations

import pathlib

MARK = "## 8. Corrections after external review, 2026-09-21"


def edit(path, pairs, append=None):
    p = pathlib.Path(path)
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        assert old in s, f'{path}: missing {old[:70]!r}'
        s = s.replace(old, new, 1)
    if append:
        s = s.rstrip('\n') + '\n\n' + append
    p.write_text(s, encoding='utf-8')


def main():
    synth = pathlib.Path('WHAT-WORKED-WHAT-FAILED-2026-09-21.md')
    if MARK in synth.read_text(encoding='utf-8'):
        raise RuntimeError('corrections already applied')

    # ---- construction results: E3 as one estimand with its own interval ----
    edit('CONSTRUCTION-IMPROVER-RESULTS-2026-09-21.md', [
        ("| **E3** growth exceeds data volume | 45 against pooled 21, margin **+24** | 49 against pooled 29, margin **+20** |",
         "| **E3** growth exceeds data volume | **+26.0**, 9w/3l, interval **+7.8 to +49.0** | **+19.0**, 10w/1l, interval **+0.2 to +38.3** (exact interval on rounded contributions **0 to +38**) |"),
        ("""Pooling the same data also improves as history grows, by +21 and +29. That is
just more data helping, and it is exactly what an improver-growth result can be
mistaken for. Construction grows +45 and +49, so the margin attributable to the
improver rather than to data volume is **+24 and +20**.""",
         """Pooling the same data also improves as history grows, by +20.2 and +29.3. That
is just more data helping, and it is exactly what an improver-growth result can
be mistaken for. Construction grows +46.2 and +48.3, so the margin attributable
to the improver rather than to data volume is **+26.0 and +19.0**.

E3 is one estimand: per transfer bank, (built at 24 minus built at 4) minus
(pooled at 24 minus pooled at 4), summed, with a paired bootstrap interval over
banks. On that interval **replication two touches zero** (bootstrap lower bound
+0.2; exact enumeration on rounded contributions, lower bound 0). Significance
of E2 and of pooled growth separately did not establish significance of their
difference. The honest reading is that E3 is clean in replication one and
marginal in replication two. Per-bank contributions and both intervals are in
`analysis/e3-single-estimand-20260921.json`.

**Correction record.** The frozen `results.json` rounded each per-bank
difference to an integer before summing, separately for E2 and for pooled
growth. That produced 45 and 21 (replication one) and 49 and 29 (replication
two) where the unrounded values are 46.2, 20.2, 48.3 and 29.3, and E3 margins
of 24 and 20 where the single-estimand values are 26.0 and 19.0. E1 was
unaffected. The rounding existed to keep the exact-enumeration interval
tractable; the corrected analysis reports a percentile bootstrap on unrounded
contributions alongside the exact interval on rounded ones."""),
    ])

    # ---- synthesis: numbers, P2b rename, prospective split, reframe, narrowing ----
    edit(synth, [
        ("| improver growth, construction form | **achieved**, purest form | two frozen replications: E1 +29 / +26, E2 +45 / +49, **E3 margin over data volume +24 / +20**; two audits, zero failures; 5 of 5 rotation folds |",
         "| improver growth, construction form | **achieved** for E1 and E2; E3 clean in one replication and marginal in the other | two frozen replications: E1 +29 / +26, E2 +46.2 / +48.3, **E3 +26.0 (interval +7.8 to +49.0) / +19.0 (interval +0.2 to +38.3)**; two audits, zero failures; 5 of 5 rotation folds; out-of-fold router audit pending |"),
        ("| recursive child-improver growth | **failed, closed for this environment** | G3 -2 (interval -15 to +12); all three candidate transmissible states screened and rejected |",
         "| recursive child-improver growth | **not found** in the tested transmission classes at the tested budgets | G3 -2 (interval -15 to +12); three candidate transmissible states screened, none clears +20 |"),
        ("| **P2b** non-stationarity | does the best action vary by instance or is it a constant | **fixed regret**: per-bank hindsight minus best constant |",
         "| **P2b** conditional action heterogeneity | does the best action vary by instance or is it a constant | **fixed regret**: per-bank hindsight minus best constant |"),
        ("""They predicted every outcome: nine action spaces failed at least one and no
improver grew in them; the tenth cleared all four and improver growth followed.""",
         """Their record must be split, because a framework built from failures cannot
be credited with predicting them. **Retrospective**: P2, P2b and P2c were
formulated across the first seven failures and explain them after the fact.
**Prospective**: the complexity partition was screened before any improver was
built for it, predicted to pass, and passed on two frozen replications; the
rule-identity and depth-heterogeneous spaces and the acquisition, regime and
failure-memory transmissible states were screened before building and rejected,
so their negatives were never tested. **Retrospective again**: the partition
scheme was screened only after the recursive experiment had failed. The
prospective hit rate is one confirmed positive and five untested rejections.
Thresholds must be frozen before the next environment family is examined;
otherwise the programme learns which benchmarks pass the screen rather than
whether the screen predicts opportunity."""),
        ("| **E3, growth exceeds data volume** | 45 vs pooled 21, **+24** | 49 vs pooled 29, **+20** |",
         "| **E3, growth exceeds data volume** | **+26.0**, interval +7.8 to +49.0 | **+19.0**, interval **+0.2 to +38.3** |"),
        ("""E3 is the gate that carries the claim. Pooling the same data grows by +21 and
+29 on its own; that is more data helping and is exactly what improver growth can
be mistaken for. Construction grows more than twice as fast.""",
         """E3 is the gate that carries the claim, and with its own paired interval it is
clean in replication one and marginal in replication two. Pooling the same data
grows by +20.2 and +29.3 on its own; that is more data helping and is exactly
what improver growth can be mistaken for. Construction grows +46.2 and +48.3.
The frozen `results.json` reported 45/21 and 49/29 because it rounded per-bank
differences before summing; the results file carries the correction record."""),
        ("### 5.2 Construction, not selection",
         "### 5.2 Residual over the default: created by construction, captured by selection"),
        ("""Every replicated gain in the programme came from **building** an evaluator
component: +35 for the first E0 reranker, +70 and +51 for the AST specialists,
+49 for the region specialists, +37 and +32 for the complexity specialists built
in-run. Every failure came from **choosing** among components already built:
training rules, thresholds, temperatures, width schedules, region purchases,
routing among frozen specialists on i.i.d. banks. The construction confirmation
is the first experiment in which the improver's action *is* construction, and
E3 shows the growth exceeds what the same data buys without it.""",
         """An earlier draft framed this as construction versus selection. That is too
strong, and the routing result refutes it: routing is selection, and it
succeeded. The supported statement is narrower. Selection fails when defaults
already capture the available value or when the remainder is unlearnable;
construction can create complementary components that leave a residual worth
selecting over. Every replicated gain, +35 for the first E0 reranker, +70 and
+51 for the AST specialists, +49 for the region specialists, +37 and +32 for the
complexity specialists built in-run, came from construction creating that
residual, and the routing and construction confirmations are the two cases in
which selection then had something to capture. The failures were selection over
menus with no residual."""),
        ("""Recursive growth is closed for this
environment: every process-level choice a parent could hand on is already made
well enough by a free default.""",
         """The defensible conclusion is that no practically sufficient recursive
advantage was found in the tested transmission classes, at the tested budgets,
under the specified endpoint. It is not a proof that every recursive mechanism
in the environment is exhausted; in particular the endpoint is accuracy, and an
inherited procedure that reached the same accuracy at lower construction cost
would not have been detected."""),
        ("""- **Recursive growth.** Not achieved, and closed for this environment through
  every transmissible state identified.""",
         """- **Recursive growth.** Not found in three tested transmission classes at the
  tested budgets under an accuracy endpoint. Not shown impossible."""),
    ], append=MARK + """

Two reviews of this document were received. The following are accepted and
applied above; each is also recorded in the results file it affects.

1. **E3 traceability.** The reviewers' endpoint arithmetic, 26.0 and 19.0, was
   right and the reported 24 and 20 were rounding artifacts. E3 is now one
   estimand with its own paired interval, and replication two's interval touches
   zero. Sections 1 and 3.5 updated.
2. **Out-of-fold routing.** In the construction runs the router was fitted on
   specialist predictions for the specialists' own training rows. The
   independent auditor reproduced that faithfully because it follows the same
   specification, which is the reviewers' point that an information-flow audit
   is not a reproduction audit. The routing confirmation is not affected: its
   specialists were trained on separate source panels and its router saw only
   out-of-sample views. An out-of-fold rerun on both construction replications,
   with capacity-matched and feature-augmented pooled baselines, is
   `construction_oof_audit.py`; its result supersedes E1 and E3 above.
3. **P2b is heterogeneity, not non-stationarity.** Per-instance variation in the
   best action exists under i.i.d. sampling, and drift need not create any
   routing opportunity. Renamed in the design document.
4. **Retrospective versus prospective.** Section 3.2 now splits the screening
   record: one confirmed prospective positive, five untested rejections.
5. **Construction versus selection** is not the divide; residual over the
   default is. Section 5.2 rewritten.
6. **"Closed for this environment"** overstated the recursive null. Narrowed to
   the tested classes, budgets and endpoint.
7. **Reproduction is not independence.** 646,028 rechecked labels establish
   computational reproducibility. The sampling unit for the improver claims is
   the transfer bank, twelve per replication; for any recursive claim it would
   have to be the whole lineage. The exact-enumeration interval assumes bank
   exchangeability and is not a coverage guarantee.
8. **Adaptive holdout reuse.** One opened panel served as the held-out target
   for the partition screen, the routing and construction development runs, the
   recursive experiment and its scheme screen, and replication one's frozen
   transfer panel was later read by the acquisition screen. A sealed replication
   set, seeds 919100 to 919311, is reserved and will not be opened until a final
   confirmatory protocol is hashed.
""")

    # ---- design doc: rename P2b ----
    edit('TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md', [
        ("**P2b. Non-stationarity precondition.**",
         "**P2b. Conditional action heterogeneity precondition** (previously named non-stationarity; the best action can vary by instance under i.i.d. sampling, and drift need not create a routing opportunity)."),
    ])

    # ---- recursive doc: narrow the conclusion ----
    edit('RECURSIVE-GROWTH-2026-09-21.md', [
        ("""**Conclusion for this environment: recursive growth is not demonstrable through
any transmissible state identified.**""",
         """**Conclusion: no practically sufficient recursive advantage was found in the
three tested transmission classes, at the tested budgets, under the accuracy
endpoint.** This is not a proof of exhaustion. An inherited procedure that
reached the same accuracy at lower construction cost would not register on this
endpoint, and the tested states do not span reusable representations, optimizer
state or search heuristics."""),
    ])

    # ---- TODO ----
    t = pathlib.Path('.claude/TODO.md')
    u = t.read_text(encoding='utf-8')
    anchor = "### Purity pass, 2026-09-21: construction, recursion, reproducibility"
    assert anchor in u
    block = """### External review, 2026-09-21: accepted items and next programme

- [x] **E3 traceability confirmed and corrected.** `compare()` rounded per-bank differences before summing; the reported 24/20 were artifacts of unrounded 26.0/19.0. Recomputed as one estimand with paired bootstrap intervals (`analysis/e3-single-estimand-20260921.json`): rep 1 **+26.0 [7.8, 49.0]**, rep 2 **+19.0 [0.2, 38.3]**, exact interval on rounded contributions **[0, 38]**. **Rep 2's E3 touches zero.** E1 unaffected (29.0, 26.0). Results and synthesis docs corrected with a correction record.
- [ ] **Out-of-fold router audit running** (`construction_oof_audit.py`, both reps). The frozen construction runs fitted the router on in-sample specialist views; the auditor reproduced it because it follows the same spec. Adds `pooled_capacity` (60 leaves) and `pooled_featured` (rows augmented with the router's five task statistics). E1/E3 recomputed for `built_oof` against all three baselines. **This supersedes the construction headline either way.** The routing confirmation is not affected: its specialists were trained on separate source panels.
- [x] P2b renamed to **conditional action heterogeneity**; "construction, not selection" reframed as residual over the default; "closed for this environment" narrowed to tested classes, budgets and endpoint; screening record split into retrospective and prospective (prospective hit rate: 1 confirmed positive, 5 untested rejections).
- [x] **Sealed replication set reserved, never to be opened until a final confirmatory protocol is hashed:** history_a 919100-919111, history_b 919200-919211, transfer 919300-919311. One opened panel (`candidate-conditioned-query-transfer`) and rep-one's frozen transfer panel have been reused for design decisions and are no longer clean.
- [ ] **Next programme, from the reviews, not started**: (1) restricted constructor language (feature derivation, partition fitting, effort allocation, specialist fitting, OOF routing, deploy rule) with the hand-written complexity constructor as baseline; (2) freeze screen thresholds, build a base family whose optimal constructor varies across bases, screen V_M for the constructor language prospectively; (3) three-arm design, fixed / constructor-only / recursive, with common-state replay probes, metaproductivity parent selection, cost-to-target as co-primary endpoint, independent lineages sized by a pilot power analysis, about 6 generations; (4) pass = both arms' lower CI > 0 versus constructor-only on 2 replications, advantage persisting at generation t+2, sealed final audit. Do not start until the OOF audit is read; if E1 falls, the constructor language needs a stronger baseline first.
- [ ] Citation checks before any writeup: read STOP, HGM, DreamCoder/LAPS and GEA (2602.04837) directly; do not cite their specific claims from the reviews.

"""
    t.write_text(u.replace(anchor, block + anchor, 1), encoding='utf-8')
    print('all corrections applied')


if __name__ == '__main__':
    main()
