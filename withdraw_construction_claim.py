"""Withdraw the construction-form improver-growth claim after the OOF and
capacity-matched audit (`construction_oof_audit.py`, both replications).

Every edit asserts its anchor exists. Refuses to run twice.
"""
from __future__ import annotations

import pathlib

MARK = "WITHDRAWN 2026-09-21 after the capacity-matched audit"

TABLE = """| `built_oof` at 24 banks against | rep 1 | rep 2 |
| --- | --- | --- |
| `pooled`, 15 leaves | E1 +15.0, interval -3.0 to +37.0; E3 +6.7, interval -12.8 to +29.8 | E1 +27.0, interval +9.0 to +45.0; E3 +13.5, interval -2.3 to +30.0 |
| **`pooled_capacity`, 60 leaves** | **E1 -50.0, interval -68.0 to -33.0**; E3 -22.0, interval -45.5 to 0.0 | **E1 -36.0, interval -51.0 to -22.0**; E3 -15.7, interval -32.3 to +0.3 |
| `pooled_featured`, 15 leaves plus router statistics | E1 +19.0, interval +2.0 to +40.0; E3 +5.8, interval -10.7 to +26.2 | E1 +33.0, interval +14.0 to +52.0; E3 +18.3, interval +2.3 to +34.7 |
| in-sample router minus OOF router | **+14.0, interval +1.0 to +27.0** | -1.0, interval -15.0 to +13.0 |

Curves, expected total per history size:

| history | rep 1 built OOF | rep 1 pooled 60 | rep 2 built OOF | rep 2 pooled 60 |
| --- | --- | --- | --- | --- |
| 4 | 316.2 | 344.2 | 316.2 | 336.5 |
| 8 | 322.5 | 366.8 | 330.8 | 363.2 |
| 16 | 337.2 | 381.0 | 353.0 | 385.2 |
| 24 | 343.0 | 393.0 | 359.0 | 395.0 |"""


def edit(path, pairs, prepend_after=None, banner=None, append=None):
    p = pathlib.Path(path)
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        assert old in s, f'{path}: missing {old[:70]!r}'
        s = s.replace(old, new, 1)
    if prepend_after and banner:
        assert prepend_after in s, f'{path}: missing anchor {prepend_after[:60]!r}'
        s = s.replace(prepend_after, prepend_after + '\n\n' + banner, 1)
    if append:
        s = s.rstrip('\n') + '\n\n' + append
    p.write_text(s, encoding='utf-8')


def main():
    results = pathlib.Path('CONSTRUCTION-IMPROVER-RESULTS-2026-09-21.md')
    if MARK in results.read_text(encoding='utf-8'):
        raise RuntimeError('already withdrawn')

    # ---- construction results: banner + withdrawal section ----
    edit(results, [],
         prepend_after="# Construction-improver growth, confirmed on frozen banks, 2026-09-21",
         banner=f"""> **{MARK}.** The E1 and E3 gates below were run
> against a pooled baseline with one quarter of the built system's leaf
> capacity, and the router was fitted on in-sample specialist views. With the
> router fitted out of fold and a single pooled model given matched capacity
> (60 leaves), the built system **loses by 50 and 36** at 24 history banks and
> E3 is negative or crosses zero against every baseline. The advantage this
> document reported was capacity, plus router leakage in replication one. E2
> alone survives, and E2 alone means "more data helps", which the pooled model
> shows too. The numbers below are retained as the record; the withdrawal
> section at the end has the audit. Source: `runs/*/oof_audit.json`.""",
         append=f"""## Withdrawal, 2026-09-21

Two review findings were checked on both frozen replications with
`construction_oof_audit.py`, which reuses the audited caches and generates
nothing.

**Out-of-fold routing.** `fit_router` was fitted on specialist predictions for
the specialists' own training rows. Refitting it on three-fold out-of-fold views
lowers the built system by **14.0** (interval +1.0 to +27.0) at 24 banks in
replication one and by -1.0 (interval -15.0 to +13.0) in replication two. The
leakage was real and it inflated one replication.

**Capacity-matched pooling.** The built system holds up to four models of 15
leaves plus a router. One pooled model with 60 leaves, on exactly the same
history, beats the out-of-fold built system at every history size in both
replications.

{TABLE}

**What this changes.**

- E1 against the protocol's own baseline drops to **+15.0 (interval crossing
  zero)** and +27.0 after out-of-fold routing. Against a capacity-matched
  baseline it is **-50.0 and -36.0**. E1 is withdrawn.
- E3 crosses zero against every baseline in at least one replication and is
  negative against the capacity-matched one in both. E3 is withdrawn.
- E2 survives: the built system improves with history (316.2 to 343.0 and 316.2
  to 359.0). So does the pooled model (344.2 to 393.0 and 336.5 to 395.0). E2
  alone establishes that more verified data helps, which is not an improver
  claim.
- Feature augmentation does not explain the gap: `pooled_featured` scores 324.0
  and 326.0, below plain pooling. The router's task statistics are not the
  source of value.

**What survives from these runs.** Verifier growth is strengthened, not
weakened: the capacity-matched pooled model beats the frozen base evaluator E0
by **+73 and +69** at 24 banks, and it is now the strongest evaluator built
inside a frozen run. The reproducibility machinery, the protocol hashing and the
independent audits performed exactly as designed; they reproduced a flawed
specification faithfully, which is the difference between a reproduction audit
and an information-flow audit.

**Why the frozen audits passed.** The auditor re-derived the runner's procedure
from the same specification, including in-sample router fitting and a 15-leaf
pooled baseline. It could not detect that the specification itself was the
problem. An information-flow audit and an adversarial-baseline check are
distinct from reproduction and must be run separately.

**Open check.** A built system whose specialists also receive 60 leaves has not
been compared against the 60-leaf pooled model. If it wins, partition structure
has value at matched capacity and would need its own frozen confirmation. If it
does not, partitioning adds nothing here beyond capacity. That comparison is
`construction_capacity_audit.py`.""")

    # ---- synthesis: outcome rows + section 8 item ----
    edit('WHAT-WORKED-WHAT-FAILED-2026-09-21.md', [
        ("| improver growth, construction form | **achieved** for E1 and E2; E3 clean in one replication and marginal in the other | two frozen replications: E1 +29 / +26, E2 +46.2 / +48.3, **E3 +26.0 (interval +7.8 to +49.0) / +19.0 (interval +0.2 to +38.3)**; two audits, zero failures; 5 of 5 rotation folds; out-of-fold router audit pending |",
         "| improver growth, construction form | **WITHDRAWN** | with out-of-fold routing and a capacity-matched (60-leaf) pooled baseline, the built system **loses by 50 and 36** at 24 banks; E3 negative or crossing zero against every baseline; router leakage inflated rep 1 by +14. Only E2 survives, and E2 is \"more data helps\", which the pooled model also shows |"),
        ("| verifier (evaluator) growth | **achieved**, purest form | built-in-run system minus frozen E0: **+37** (interval +20 to +56) and **+32** (+18 to +44); pooled minus E0 only +8 and +6, both crossing zero |",
         "| verifier (evaluator) growth | **achieved**, strengthened | the strongest evaluator built inside a frozen run is now a capacity-matched pooled model: **+73 and +69** over frozen E0 at 24 banks; region specialists +49 (interval +37 to +62) on fresh banks, audited |"),
    ], append=f"""9. **Construction-form improver growth is withdrawn.** The out-of-fold and
   capacity-matched audit (`construction_oof_audit.py`) on both frozen
   replications found that one pooled model with 60 leaves beats the built
   system by **50 and 36** at 24 banks, at every history size, with intervals
   entirely negative, and that in-sample router fitting had inflated
   replication one by **+14** (interval +1 to +27). E3 crosses zero or is
   negative against every baseline. E2 survives and means only that more
   verified data helps, which the pooled model demonstrates too. The reviewers
   named capacity-matched pooling as the largest risk to the headline; it was
   the actual flaw. Sections 1 and 3.5 are superseded by this item and by the
   withdrawal section of the results file. Verifier growth is strengthened by
   the same audit: the capacity-matched pooled model beats E0 by +73 and +69.
   The routing-form claim was not examined by this audit and has not been
   compared against a capacity-matched pooled model; that check is owed.""")

    # ---- measurement contract ----
    edit('INTELLIGENCE-GROWTH-MEASUREMENT.md', [
        ("**Update, 2026-09-21 (later): the PURER construction claim is also achieved.**",
         "**Update, 2026-09-21 (later): the construction claim below is WITHDRAWN.** An out-of-fold and capacity-matched audit on both frozen replications found a single 60-leaf pooled model beats the built system by 50 and 36 at 24 banks, and in-sample router fitting inflated replication one by +14. E3 crosses zero or is negative against every baseline; only E2 (\"more data helps\") survives. See the withdrawal section of `CONSTRUCTION-IMPROVER-RESULTS-2026-09-21.md`. The original text follows for the record.\n\n**Original, superseded:**"),
    ])

    # ---- memory ----
    mem = pathlib.Path(r'C:\Users\reese\.claude\projects\C--Users-reese\memory\rsi-project.md')
    m = mem.read_text(encoding='utf-8')
    start = m.index("- **Construction** improver growth also achieved and audited:")
    end = m.index("\n", start)
    m = (m[:start]
         + "- **Construction** improver growth was claimed, then **WITHDRAWN 2026-09-21**: a capacity-matched (60-leaf) pooled model beats the built system by 50 and 36 at 24 banks, and in-sample router fitting inflated rep 1 by +14. Only E2 (\"more data helps\") survives. **Lesson: reproduction audits reproduce flawed specs faithfully; always add an adversarial capacity-matched baseline and an out-of-fold information-flow check.** Verifier growth strengthened (pooled-60 beats E0 by +73/+69)."
         + m[end:])
    mem.write_text(m, encoding='utf-8')

    # ---- TODO ----
    t = pathlib.Path('.claude/TODO.md')
    u = t.read_text(encoding='utf-8')
    old = "- [ ] **Out-of-fold router audit running**"
    idx = u.index(old)
    end = u.index("\n", idx)
    new_line = ("- [x] **OOF + capacity-matched audit DONE, and it withdraws the construction claim.** `built_oof` at 24 banks: vs `pooled` E1 +15 (rep 1, interval crossing zero) / +27; vs **`pooled_capacity` (60 leaves) E1 -50 [-68, -33] and -36 [-51, -22]**; E3 negative or crossing zero against every baseline; in-sample router leakage inflated rep 1 by **+14 [1, 27]**. `pooled_featured` does not explain it (324, 326). Only E2 survives and it is \"more data helps\". Withdrawal banner and section added to the results doc; synthesis, measurement contract, memory and ledger updated. Verifier growth strengthened: pooled-60 beats E0 by +73/+69.\n"
                "- [ ] **Capacity-matched built vs capacity-matched pooled** (`construction_capacity_audit.py`): specialists at 60 leaves with OOF router against pooled-60 and pooled-120. If built-60 wins, partition structure has value at matched capacity and needs its own frozen confirmation; if not, partitioning adds nothing beyond capacity here.\n"
                "- [ ] **Owed: routing confirmation vs capacity-matched pooled.** The routing runs have no feature caches; build them, then compare the routed four-specialist system against a 60-leaf pooled model on the same 24 history banks. The routing claim (C1/C2) is about learning to route and stands on its own terms, but the reviewers' residual-over-default framing requires this check before it is called the best use of that history.")
    u = u[:idx] + new_line + u[end:]
    t.write_text(u, encoding='utf-8')

    # ---- ledger ----
    edit('REPRODUCIBILITY-LEDGER-2026-09-21.md', [], append="""## Amendment, 2026-09-21: construction runs

The two construction runs remain computationally reproducible and their audits
remain valid as reproduction audits. Their **claim is withdrawn**: the
specification they reproduce fits the router on in-sample specialist views and
compares against a pooled baseline with one quarter of the built system's leaf
capacity. `runs/construction-improver-confirmation-*/oof_audit.json` holds the
out-of-fold and capacity-matched rerun on the same caches. A reproduction audit
cannot detect a flawed specification; information-flow and adversarial-baseline
checks are separate steps and are now required before any gate result is
reported.""")
    print('construction claim withdrawn across docs, memory and TODO')


if __name__ == '__main__':
    main()
