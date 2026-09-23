# Kyberos Strategy of Record (2026-07)

Adopted from the GTM/fundraising research report (2026-07). This file is the
site's source of truth for positioning; copy changes trace here.

## Mission (2026-09-16, supersedes everything below that conflicts)

**Kyberos is 100% dedicated to trustworthy agents and recursive
self-improvement (RSI). Nothing else.** Every page, product and claim either
serves one of those two or comes off the site.

They are one mission, not two. The failure mode of an agent on a long task and
the failure mode of a self-improving system are the same: a record of its own
past that is narrative rather than measurement. An agent planning against a
story it told itself drifts; a system grading its own improvement finds the
grader's blind spots. Kyberos's substrate (sensor-verified state, hash-chained
journal, bit-exact replay, signed receipts) is the answer to both, so RSI is
where the verification work leads, not a new line of business.

## Positioning (one sentence)

> **Kyberos builds AI you can prove: agents whose every decision is measured,
> traceable, and replayable, and self-improvement that only counts evidence it
> can't fake.**

- Category: **Verifiable AI** (agent reliability / provenance / auditability),
  extended to **verifiable self-improvement**.
- Brand attitude (voice, not thesis): anti-hype; every claim traceable to an
  artifact.
- **RSI honesty rule.** The verification substrate is shipped. RSI proper
  (training on sensor rewards, learned planners) is research and is labelled
  as research everywhere it appears. Never imply a self-improving system
  exists that does not.

## Product hierarchy

- **Lead product: GATS** — neuro-symbolic agent framework. Neural inference
  only at decision points; the plan lives as a graph; provenance by
  construction; deterministic replay; token cost tracks decisions, not
  history. Positioned as the planning-and-provenance layer **complementary to
  LangGraph et al., not a competing framework**.
- **Second product: LEDGER** — the audit-first coding agent, GATS discipline
  applied to a workflow we run ourselves.
- **Proof asset: the integration lab** — six simulated customer stacks, each
  attacked with prompt-injected lies, tampered audit logs, and injected
  crashes. It is the evidence engine, not a product line.
- **Research program: RSI** at `/rsi`. Built on GATS §14: sensors are the
  verifier, worktrees are rollout infrastructure, the journal is the trajectory
  store, and any learned change is promoted only if replay variance stays zero.
  Shipped today: a world model that learns only from sensor-verified outcomes,
  and never learns a refusal as a fact.
- **Live demo: the agent console** at `/agent`. Kept as a working example of
  agent discipline a non-technical visitor can drive: it asks instead of
  guessing, shows its whole plan before running, and has an approval mode.
  It is a demo, not a product line, and it does not produce LEDGER receipts;
  never say it does.
- Roadmap sentence: *"We monetize GATS first (design partners in agent
  reliability); the integration lab is our public proving ground, the free
  audit is how prospects meet it, and RSI is the research the substrate was
  built for."*

**Scope (2026-09-16):** trustworthy agents and RSI only. The robotics RL proof
asset was retired 2026-08; the pages, assets, and market research are in
`git log` if the decision is ever revisited.

## ICP & wedge (the one buyer)

Teams deploying LLM agents in **regulated or high-stakes workflows** —
fintech ops, compliance, healthcare back-office — who must **audit and
reproduce every agent decision** (EU AI Act enforcement from 2 Aug 2026;
internal governance). Pain: non-determinism, opacity, uncontrolled inference
cost.

## Value translations (tech → buyer)

- Deterministic replay → "reproduce any agent decision for audit/debug."
- Graph provenance → "regulator-ready audit trail by construction."
- Inference only at decision points → "costs scale with decisions, not
  conversation length."
- FAILED-runs-as-data + QA verdicts → "we catch reliability failures before
  you ship."

## Benchmark claims (honesty rules)

GATS numbers are from our own arXiv paper (2607.08894), which reports TWO
benchmarks — always label which one is being cited:
- Main synthetic suite (100 tasks): GATS 100% vs LATS 92.0% / ReAct 64.0%
- Stress test (12 scenarios, 120 tasks): GATS 100% vs LATS 88.9% / ReAct 23.9%
- Both: zero LLM calls at inference for GATS (~37/task for LATS), zero
  variance across runs.
Always cited with the synthetic/stress-test caveat; real-workflow demos are
the active work item.

## Website architecture (implemented)

Home (hero + animated core idea + split CTA) · /graph-agents = GATS product
page (benchmark table, L1/L2/L3, wedge, self-serve replay) · /ledger =
LEDGER product page · /audit (free agent audit, the primary top-of-funnel)
· /design-partners (program + ICP) · /investors (email-gated brief request)
· /rsi (research program, roadmap labelled as roadmap) · /agent (live demo,
not a product). Nav lives once in `src/landing/navLinks.js`; its CTA is the
free audit, not the demo, because the demo is off the buyer's path.

## Stage checklist

- [x] Positioning adopted; GATS lead.
- [x] Homepage above the fold: one sentence, live artifact, split CTA.
- [x] ICP + wedge written (this file + /design-partners).
- [x] Self-serve GATS replay demo (`GatsReplay` on /graph-agents).
- [x] Site narrowed to agents only (2026-08).
- [ ] NVIDIA Inception + Microsoft Founders Hub applications (reese).
- [ ] Buyer-framed benchmark page w/ cost numbers from a real workflow.
- [ ] 3-5 design partners signed; page updated with count/quotes.
- [ ] 2-3 named advisors recruited and published (reese).
- [ ] Gated data room (Peony/Carta Launch) with papers, galleries, deck, SAFE.
