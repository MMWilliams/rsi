"""Final document pass after the capacity-matched audits.

Records that (1) the complexity-partition environment fails P2d against a
capacity-matched default and is withdrawn as a qualifying environment, (2) both
improver-growth forms are dominated by a single larger pooled model, so no
RSI-relevant improver growth is demonstrated, (3) verifier growth is
strengthened, and (4) P2c's adversarial default must include model capacity.

Every edit asserts its anchor. Refuses to run twice.
"""
from __future__ import annotations

import pathlib

MARK = "## 9. Final position after the capacity-matched audits"


def edit(path, pairs=(), append=None):
    p = pathlib.Path(path)
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        assert old in s, f'{path}: missing {old[:70]!r}'
        s = s.replace(old, new, 1)
    if append:
        s = s.rstrip('\n') + '\n\n' + append
    p.write_text(s, encoding='utf-8')


def replace_line_starting(path, prefix, new_line):
    p = pathlib.Path(path)
    s = p.read_text(encoding='utf-8')
    i = s.index(prefix)
    j = s.index('\n', i)
    p.write_text(s[:i] + new_line + s[j:], encoding='utf-8')


def main():
    synth = pathlib.Path('WHAT-WORKED-WHAT-FAILED-2026-09-21.md')
    if MARK in synth.read_text(encoding='utf-8'):
        raise RuntimeError('final pass already applied')

    # ---------------------------------------------------------- synthesis ----
    edit(synth, [
        ("| verifier (evaluator) growth | **achieved**, strengthened | the strongest evaluator built inside a frozen run is now a capacity-matched pooled model: **+73 and +69** over frozen E0 at 24 banks; region specialists +49 (interval +37 to +62) on fresh banks, audited |",
         "| verifier (evaluator) growth | **achieved**, and it is the only growth claim that survives | a single larger pooled model on more verified labels is a better evaluator: pooled-60 beats frozen E0 by **+73 and +69** on the frozen construction transfer panels; pooled-120 beats E0 by roughly +90 on the opened screen panels; region specialists +49 (interval +37 to +62), audited |"),
        ("### 3.3 The complexity-partition environment",
         """### 3.3 The complexity-partition environment (withdrawn as qualifying; see section 9)

> **Superseded 2026-09-21.** Re-screened with model capacity in the
> adversarial default (`partition_rescreen_capacity.py`), a single 120-leaf
> pooled model scores 412, 405 and 413 on the three screen panels, above the
> partition's own latent oracle routing at 392, 401 and 400, and the held-out
> selector loses to it by 2 (interval -10 to +7). **P2d fails.** The section
> below is retained as the record of what was believed and why."""),
    ], append=MARK + """

After the reviews, three further checks were run on the frozen caches and the
opened screen panels, each adding a single larger pooled model to the set of
zero-knowledge defaults. That one addition changes the programme's conclusion.

| check | finding |
| --- | --- |
| construction, out-of-fold router | leakage inflated replication one by **+14** (interval +1 to +27) |
| construction, 60-leaf pooled baseline | beats the built system by **50 and 36** at 24 banks; E3 negative or crossing zero everywhere |
| construction, 60-leaf specialists too | still trails pooled-60 by 9 to 15 at sizes 4 and 8, and pooled-120 by more; partitioning costs at matched capacity |
| routing, 60-leaf pooled on the same history | beats the routed system by **35 and 29**; with the specialists' source labels, by **62 and 37**, every interval negative |
| partition environment, 120-leaf pooled default | beats the latent own-bin oracle on all three screen panels; **P2d fails**, selector -2 (interval -10 to +7) |

**What stands.** Verifier growth: a larger model on more verified labels is a
better evaluator, replicated, audited, and now the strongest component built in
any frozen run. The four preconditions as a screening framework. The
reproducibility machinery, which reproduced every specification faithfully. The
two baseline rules from earlier in the day. The recursive null, narrowed.

**What does not.** No learned improver in this programme produced a system
that beats the strongest free procedure on the same labels. Both forms of
improver growth hold in the measurement contract's literal sense, a later
checkpoint beats an earlier one from the same base, and both are dominated by
"fit one larger model", which needs no improver. The complexity partition was
not latent structure; it was four small models outperforming one small model.
By the adversarial-default standard the programme itself adopted, applied with
model capacity in the default set, **no RSI-relevant improver growth is
demonstrated in any form.**

**The single rule that would have caught all of it in one screen.** P2c's
adversarial default set must contain model capacity, a single larger model on
the same labels, and not only hand-written rules. Every apparent improver result
here was measured against defaults that had less capacity than the improver's
output. The reviewers named this as the largest risk to the headline before any
of these checks were run; they were right, and the framework was one clause
short of catching it itself.

**On the reviews' proposed next programme.** A restricted constructor
language, a three-arm lineage design and common-state replay remain the right
shape for a recursive test. But this outcome moves the prerequisite: before any
constructor language is built, the target environment must be shown to have
residual value over a capacity-matched pooled default, and the constructor
language must be able to express "one larger model" so that it can only win by
doing something a larger model cannot. Otherwise the next programme rediscovers
this one.""")

    # --------------------------------------------- measurement contract ----
    edit('INTELLIGENCE-GROWTH-MEASUREMENT.md', [
        ("**Update, 2026-09-21: improver growth is ACHIEVED, replicated and audited.**",
         "**Update, 2026-09-21 (final): the routing claim below holds as stated and is DOMINATED.** A single 60-leaf pooled model on the same 24 history banks beats the routed system by 35 and 29, and by 62 and 37 with the specialists' source labels, every interval negative (`runs/complexity-improver-confirmation*/capacity_check.json`). The complexity-partition environment fails P2d against a 120-leaf pooled default (`analysis/partition-rescreen-capacity-20260921.json`). With model capacity in the adversarial default set, **no RSI-relevant improver growth is demonstrated in any form**; verifier growth is strengthened. The original text follows for the record.\n\n**Original, superseded:**"),
    ])

    # -------------------------------------------------- design document ----
    edit('TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md', [
        ("**P2c. Default-regret precondition.** P2 and P2b are both necessary and still\nnot sufficient.",
         "**P2c. Default-regret precondition.** P2 and P2b are both necessary and still\nnot sufficient. **The adversarial default set must include model capacity: a\nsingle larger model fitted on the same labels, at several sizes, not only\nhand-written rules.** On 2026-09-21 this clause was missing, and every improver\nresult in the programme was measured against defaults with less capacity than\nthe improver's output; a 60-leaf pooled model dominated all of them and a\n120-leaf model beat the partition environment's own latent oracle routing."),
    ])

    # ------------------------------------------------------------- ledger ----
    edit('REPRODUCIBILITY-LEDGER-2026-09-21.md', append="""## Amendment, 2026-09-21: routing runs and the partition environment

The routing runs reproduce to the integer under an independent reimplementation
(`routing_capacity_check.py`: routed 351.0 / 366.0, most-confident 329.0 /
343.0). Their C1 and C2 gates stand as stated. Against a capacity-matched
pooled model on the same history they are dominated by 35 and 29
(`runs/complexity-improver-confirmation*/capacity_check.json`). The
complexity-partition environment fails P2d when a 120-leaf pooled model is in
the default set (`analysis/partition-rescreen-capacity-20260921.json`). The
frozen artifacts, hashes and audits are unchanged; what changed is the
adversarial default they should have been measured against.""")

    # ------------------------------------------------------------- memory ----
    mem = r'C:\Users\reese\.claude\projects\C--Users-reese\memory\rsi-project.md'
    replace_line_starting(mem, "description:",
        "description: RSI seed-improver research at projects/rsi; verifier growth stands, every improver claim dominated by a capacity-matched pooled model (2026-09-21 review outcome)")
    replace_line_starting(mem, "**Both growth claims are now achieved, replicated and independently audited.**",
        "**2026-09-21 final outcome: verifier growth stands; NO RSI-relevant improver growth in any form.** Every improver result (routing C1/C2, construction E1-E3, the complexity-partition environment) was measured against defaults with less model capacity than the improver's output. A single 60-leaf pooled model on the same labels beats the routed system by 35/29 and the built system by 50/36; a 120-leaf model beats the partition's latent oracle routing. The partition was four small models beating one small model, not structure. Details in `WHAT-WORKED-WHAT-FAILED-2026-09-21.md` section 9.")
    edit(mem, append="""**The rule that would have caught it in one screen (2026-09-21):** P2c's adversarial default set MUST include model capacity, i.e. one larger model on the same labels at several sizes, not only hand-written rules. External reviewers named capacity-matched pooling as the largest risk before any check ran; they were right. Any future constructor language must be able to express "one larger model" so it can only win by doing something a larger model cannot.""")

    idx = pathlib.Path(r'C:\Users\reese\.claude\projects\C--Users-reese\memory\MEMORY.md')
    s = idx.read_text(encoding='utf-8')
    old = "- [RSI seed improver](rsi-project.md) evaluator AND improver growth both ACHIEVED + audited 2026-09-21; 4 preconditions gate every improver test; never benchmark growth against a one-observation baseline"
    assert old in s
    idx.write_text(s.replace(old,
        "- [RSI seed improver](rsi-project.md) verifier growth stands; EVERY improver claim withdrawn or dominated 2026-09-21 by a capacity-matched pooled model; adversarial default MUST include model capacity", 1),
        encoding='utf-8')

    # --------------------------------------------------------------- TODO ----
    t = pathlib.Path('.claude/TODO.md')
    u = t.read_text(encoding='utf-8')
    anchor = "- [ ] **After all three audits land (capacity-matched built rep 2, routing rep 2, partition re-screen): full document pass.**"
    assert anchor in u
    i = u.index(anchor); j = u.index('\n', i)
    u = (u[:i]
         + "- [x] **Partition environment re-screened with capacity in the default: FAILS P2d.** pooled-120 scores 412/405/413 on the three screen panels, above the latent own-bin oracle routing (392/401/400); latent minus best free = -20 [-41, 0], -4 [-17, 11], -13 [-31, 6]. P2c passes numerically only because the per-task oracle spans seven models; held-out selector 411 vs pooled-120 413, **-2 [-10, 7]**. The environment is withdrawn as qualifying. The partition was four 15-leaf models beating one 15-leaf model.\n"
         + "- [x] **Full document pass done** (`final_review_pass.py`): synthesis section 9, measurement contract, design doc (P2c now requires model capacity in the adversarial default), ledger, memory. **Final position: verifier growth stands; no RSI-relevant improver growth demonstrated in any form.** Contract-literal gates (C1/C2, E2) stand; every improver output is dominated by one larger pooled model on the same labels.\n"
         + "- [ ] Capacity-matched built (60-leaf specialists) audit still running; confirmatory only. When it lands, append its full table to the withdrawal section of `CONSTRUCTION-IMPROVER-RESULTS-2026-09-21.md`.\n"
         + "- [ ] **Before any next programme**: the target environment must show residual value over a capacity-matched pooled default at several sizes, and any constructor language must be able to express \"one larger model\". Otherwise the three-arm design rediscovers this outcome."
         + u[j:])
    t.write_text(u, encoding='utf-8')
    print('final pass applied')


if __name__ == '__main__':
    main()
