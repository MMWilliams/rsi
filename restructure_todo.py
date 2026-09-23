"""Split the 419-line TODO into a working list and a dated archive.

Lines 1 to 245 are the 2026-09-20/21 programme, now mostly complete. They move
to `.claude/ARCHIVE-2026-09-21-growth-programme.md` verbatim, and the TODO head
is replaced with a compact current-state block plus the genuinely open items.
Everything from the Kyberos section onward is untouched pre-existing state.

Run once from the project root.
"""
from __future__ import annotations

import pathlib

TODO = pathlib.Path('.claude/TODO.md')
ARCHIVE = pathlib.Path('.claude/ARCHIVE-2026-09-21-growth-programme.md')
SPLIT = '## Kyberos mission and evidence (2026-09-16)'

HEAD = """# RSI to-do

## Status, 2026-09-21

**No growth claim survives. The programme's output is an instrument, not a
result.** Full account: `WHAT-WORKED-WHAT-FAILED-2026-09-21.md`. The day's
completed work is archived in
`.claude/ARCHIVE-2026-09-21-growth-programme.md`.

| claim | status |
| --- | --- |
| improver growth, routing | C1 +22/+23 and C2 +36/+47 hold as stated and reproduce to the integer, but one 60-leaf pooled model on the same history beats the routed system by 35 and 29 |
| improver growth, construction | withdrawn: capacity-matched pooled beats the built system by 50 and 36; in-sample router fitting inflated rep 1 by +14 |
| verifier growth | within-distribution only: worse than base E0 on **every** held-out mechanism (716 vs 1020), and the regression worsens with capacity |
| recursive growth | not found in three tested transmission classes |
| intelligence growth (adopted definition) | none demonstrated |

**Every transfer number in this repository is instance-level.** All frozen
panels are fresh seeds of the same six generators.

### The four rules that came out of it

1. **P2 / P2b / P2c / P2d** screen an action space before an improver is built
   for it (`TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md`). Screen the
   *transmissible state* too, before any recursive machinery.
2. **The adversarial default must include model capacity**: one larger model on
   the same labels, at several sizes. This clause was missing and it ended every
   improver claim.
3. **Score a small-history arm as an expectation over windows**, never one
   predeclared seed. One draw made two replications disagree by 54 points.
4. **Every evaluator claim reports held-out-mechanism performance at the
   deployed capacity**, and must not regress below the base there.

Reproduction audits reproduce flawed specifications faithfully. Reproduction,
information-flow, adversarial-baseline and mechanism-holdout checks are four
separate required steps.

## Open

### Decision required before any of it starts

- [ ] **Capacity-to-learn programme** (`PROGRAMME-TARGET-INTELLIGENCE-GROWTH-2026-09-21.md`).
      Four procedurally generated domains with instance/composition/mechanism
      splits (three do not exist), a multidimensional IRT model calibrated
      against a capacity-scaled reference population, a research forecaster with
      prospectively committed proper-scored predictions, and a five-arm
      factorial over independent lineages for about six generations with
      common-state replay, evaluator-swap and inheritance-reset probes. Weeks of
      compute on this machine before any battery exists. **Not started; this is
      an investment decision, not a next step.**

### Cheap and runnable now

- [ ] Partitioned-vs-pooled at matched capacity, properly powered. The only
      unresolved signal: E3 vs pooled-60 was +14.7 (interval +0.3 to +30.3) and
      +8.3 (crossing zero). Needs pooled models at 60/120/240 in the default set
      and far more than twelve banks per replication. **Screen first**: default
      regret against the largest pooled model must clear +20 or it is not worth
      running.
- [ ] Record CPU time, peak memory and failed-run counts. Never captured; the
      cost ledger is labels and wall time only.
- [ ] Read STOP, HGM, DreamCoder/LAPS, GEA (2602.04837), Chollet, tinyBenchmarks,
      the emergent-abilities mirage paper, observational scaling laws, TRACED,
      ProcessBench, reward-model overoptimization and the Red Queen Gödel
      Machine **directly** before citing any of them. The reviews' summaries are
      not a substitute.

### Sealed, do not open

- [ ] Replication set **919100-919111 / 919200-919211 / 919300-919311** is
      reserved and must not be opened until a final confirmatory protocol is
      hashed. One opened panel (`candidate-conditioned-query-transfer`) and
      replication one's frozen transfer panel have both informed design
      decisions and are no longer clean.

### Older threads, unchanged

Carried forward from before 2026-09-20; none was revisited this cycle.

"""


def main():
    text = TODO.read_text(encoding='utf-8')
    index = text.index(SPLIT)
    head, tail = text[:index], text[index:]

    ARCHIVE.write_text(
        "# Archive: growth programme, 2026-09-20 to 2026-09-21\n\n"
        "Completed work, moved out of `.claude/TODO.md` on 2026-09-21 to keep\n"
        "that file usable. Retained verbatim as the record of what was run, in\n"
        "what order, and what each result turned out to be worth. The narrative\n"
        "account is `WHAT-WORKED-WHAT-FAILED-2026-09-21.md`.\n\n"
        + head[head.index('## Primary outcome'):],
        encoding='utf-8')

    TODO.write_text(HEAD + tail, encoding='utf-8')
    print('archive lines:', len(ARCHIVE.read_text(encoding='utf-8').split('\n')))
    print('todo lines:', len(TODO.read_text(encoding='utf-8').split('\n')))


if __name__ == '__main__':
    main()
