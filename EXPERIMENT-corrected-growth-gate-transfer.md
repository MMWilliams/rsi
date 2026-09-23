
# Corrected improver-growth gate, replications three and four

Predeclared 2026-09-20, before any bank for these replications is generated.

## Why a corrected gate

`EXPERIMENT-contextual-improver-transfer.md` scored the small-history parent as
one development bank fixed by lowest seed. That made the gate a measurement of
the baseline draw:

| | replication one | replication two |
| --- | --- | --- |
| `initial` total | 46 | 92 |
| best constant | 104 | 92 |
| `later` total | 126 | 118 |
| G2 | +80, interval +17 to +146, **passed** | +26, interval -1 to +62, **failed** |

`analysis/history-size-curve-20260920.json` shows single-bank parents span 46 to
104 with mean 75, so which bank `initial` held decided the outcome. Replication
one drew near the floor; replication two drew a bank equal to the best constant,
leaving nothing for history to buy.

The correction scores a small-history parent as its **expected** value over every
contiguous window of that size, paired by transfer bank. Applied post hoc to
replication one it gives +51, nine wins and two losses, interval +18 to +85.

That post hoc number cannot be a pass. A gate redesigned after seeing results has
to be predeclared and run on banks that did not exist when it was written, which
is what this protocol does.

## Design

Identical to the previous protocol in every respect except the scoring of the
small-history arm. Same generator, same Beta(0.4, 0.4) share prior, same three
actions, same nearest-share selection rule, same controls, same environment
preconditions.

- Small-history arm: expected per-transfer-bank gain of a **one**-bank parent,
  averaged over all twelve contiguous single-bank windows of the development
  panel.
- Large-history arm: the **twelve**-bank parent.
- Both arms deploy under the identical rule; only the history differs.

## Banks

Fresh seeds, never used.

- Replication three: dev 910100-910111, transfer 910200-910211, balanced control
  910300-910311.
- Replication four: dev 911100-911111, transfer 911200-911211, balanced control
  911300-911311.

## Gates

Correct zero-query top choices per 576 tasks, paired at bank level, exact bank
bootstrap.

- **P2b, environment.** Both beta panels must show fixed regret above +20 and
  the balanced control at or below +20. If not, that replication is void and
  reports no gate result.
- **C1, corrected improver growth.** Large-history minus expected small-history
  on the transfer panel. Pass requires: gain **>= +20**; at most 4 of 12 losing
  banks; interval excludes zero. The +20 threshold is the programme's existing
  P2b threshold, carried over deliberately rather than set from the observed
  +51.
- **C2, contextual value.** Large-history minus the best constant, which is
  chosen with final labels and is not deployable. Pass requires gain > 0 and
  interval excluding zero. C2 failed in both previous replications (+22 and +26,
  both intervals crossing zero) and is the weaker of the two claims.
- **C3, stationarity control.** C1 recomputed on the balanced panel, expected
  **not** to pass. A C1 pass on beta together with a C3 null is the evidence
  that the result comes from non-stationarity. In replication one this check
  misbehaved; in replication two it behaved as predicted.

## Reporting rule

**Reliable improver growth is claimed only if C1 passes on both replication
three and replication four, each with a passing independent audit.** A single
pass is reported as a single pass and nothing more. C2 and C3 are reported
separately and do not substitute for C1.

If C1 passes twice while C2 fails twice, the claim is explicitly limited to
growth in *estimating the best action*, not growth in *conditioning on the
instance*, and the results file must say so in its headline.

## Declared limits

- One synthetic benchmark, one mechanism axis, three actions.
- Specialists are the frozen 2026-09-18 models and are not retrained here.
- The large-history arm remains a single parent, so its own draw is not averaged
  over; only the small arm's is. This is deliberate, because the claim concerns
  what a *specific* accumulated history buys over a typical short one.
- Contiguous windows within one development panel are not independent samples.
- Nothing here tests recursive child-improver growth.
