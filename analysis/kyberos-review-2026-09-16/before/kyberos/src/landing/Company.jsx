/**
 * Company: kyberos.ai root, per STRATEGY-2026.md: 100% trustworthy agents and
 * RSI, nothing else. "AI you can prove." GATS leads; the proof is the
 * integration lab and the deterministic replay; RSI is where it leads.
 * Above the fold: one sentence, one animated explainer of the core idea,
 * split-funnel CTA (design partner primary / research secondary).
 */

import { Nav } from './Nav.jsx';
import { PIP_INSTALL, VERSION } from './ledgerRelease.js';
import { NAV_LINKS } from './navLinks.js';
import { GraphHero } from './GraphHero.jsx';

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600&display=swap');
.co { --bg:#ffffff; --surface:#f6f6f4; --ink:#141518; --ink2:#45464a; --muted:#7c7d79;
  --ring:rgba(0,0,0,.12); --accent:#2b6cd4; --good:#0d7f0d; --bad:#bd3030;
  background:var(--bg); color:var(--ink);
  position:fixed; inset:0; overflow-y:auto; overflow-x:hidden;
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif; -webkit-font-smoothing:antialiased; }
.co * { box-sizing:border-box; margin:0; }
.co a { color:inherit; text-decoration:none; }
.co-wrap { max-width:1120px; margin:0 auto; padding:0 24px; }
.co-hero { display:grid; grid-template-columns:1.05fr 1fr; gap:44px; align-items:center; padding:56px 0 64px; }
@media (max-width:900px){ .co-hero { grid-template-columns:1fr; } }
.co-eyebrow { font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--accent); font-weight:650; margin-bottom:14px; }
.co-hero h1 { font-size:clamp(34px,4.8vw,56px); line-height:1.05; letter-spacing:-.02em; font-weight:750; }
.co-hero p.sub { color:var(--ink2); font-size:17px; line-height:1.6; margin-top:18px; max-width:32em; }
.co-cta { display:flex; gap:12px; margin-top:26px; flex-wrap:wrap; align-items:center; }
.co-btn { display:inline-block; color:var(--accent); font-weight:650; font-size:14.5px;
  padding:12px 26px; border-radius:99px;
  background:#fff url('/assets/buttons/btn-ghost.webp') center/cover no-repeat;
  border:1px solid rgba(43,108,212,.40);
  box-shadow:0 2px 10px rgba(20,30,60,.06);
  transition:transform .15s, box-shadow .15s, border-color .15s; }
.co-btn:hover { border-color:var(--accent); transform:translateY(-1px);
  box-shadow:0 6px 16px rgba(43,108,212,.18); }
.co-link { color:var(--ink2); font-size:14px; border-bottom:1px solid var(--ring); padding-bottom:2px; }
.co-link:hover { color:var(--ink); }
.co-shot { border:1px solid var(--ring); border-radius:14px; overflow:hidden; background:var(--surface);
  box-shadow:0 18px 50px rgba(0,0,0,.14); }
.co-shot .bar { display:flex; gap:6px; padding:10px 12px; border-bottom:1px solid var(--ring); }
.co-shot .bar i { width:9px; height:9px; border-radius:50%; background:var(--ring); }
.co-shot video { display:block; width:100%; }
.co-cap { font-size:12px; color:var(--muted); padding:9px 13px; border-top:1px solid var(--ring); line-height:1.5; }
.co-why { padding:64px 0 70px; border-top:1px solid var(--ring); }
.co-why h2 { font-family:'Playfair Display',Georgia,'Times New Roman',serif; font-weight:500;
  color:var(--accent); font-size:clamp(38px,5vw,58px); text-align:center; letter-spacing:.04em;
  margin-bottom:52px; }
.co-whygrid { display:grid; grid-template-columns:1fr 1fr; gap:26px; }
@media (max-width:820px){ .co-whygrid { grid-template-columns:1fr; } }
.co-whycard { background:#f4f4fb; padding:22px; overflow:hidden; display:flex; flex-direction:column; }
.co-whycard .wn { font-family:ui-monospace,Consolas,monospace; font-size:12px; color:var(--accent); margin-bottom:10px; }
.co-whycard h3 { font-family:'Playfair Display',Georgia,serif; font-weight:500; color:var(--accent);
  font-size:24px; line-height:1.18; letter-spacing:.03em; text-transform:uppercase; margin-bottom:12px; }
.co-whycard p { font-size:13.5px; color:var(--ink2); line-height:1.6; flex:1; }
.co-sect { padding:56px 0; border-top:1px solid var(--ring); }
.co-sect h2 { font-size:26px; font-weight:720; letter-spacing:-.01em; }
.co-sect .lead { color:var(--ink2); margin-top:10px; max-width:46em; line-height:1.6; }
.co-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:16px; margin-top:30px; }
.co-card { background:var(--surface); border:1px solid var(--ring); border-radius:14px; padding:22px; }
.co-card .n { font-size:12px; color:var(--accent); font-weight:700; letter-spacing:.08em; margin-bottom:10px; }
.co-card h3 { font-size:16px; font-weight:650; margin-bottom:8px; }
.co-card p { font-size:13.5px; color:var(--ink2); line-height:1.6; }
.co-bench { width:100%; border-collapse:collapse; margin-top:24px; font-size:14px; }
.co-bench th { text-align:left; font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted);
  padding:9px 12px; border-bottom:1px solid var(--ring); }
.co-bench td { padding:10px 12px; border-bottom:1px solid rgba(0,0,0,.06); color:var(--ink2);
  font-variant-numeric:tabular-nums; }
.co-bench td b { color:var(--ink); }
.co-bench .hl td { color:var(--ink); background:rgba(57,135,229,.07); }
.co-fine { font-size:12px; color:var(--muted); margin-top:10px; line-height:1.55; }
.co-stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:14px; margin-top:28px; }
.co-stat { background:var(--surface); border:1px solid var(--ring); border-radius:14px; padding:18px 20px; }
.co-stat b { display:block; font-size:26px; font-weight:750; letter-spacing:-.01em; color:var(--accent);
  font-variant-numeric:tabular-nums; margin-bottom:6px; }
.co-stat span { font-size:13px; color:var(--ink2); line-height:1.55; }
.co-proof { display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:16px; margin-top:30px; }
.co-proofcard { border-left:3px solid var(--accent); padding:4px 0 4px 18px; }
.co-proofcard h3 { font-size:15px; margin-bottom:6px; }
.co-proofcard p { font-size:13.5px; color:var(--ink2); line-height:1.6; }
.co-founder { display:flex; gap:24px; margin-top:26px; flex-wrap:wrap; align-items:baseline; }
.co-founder .who { max-width:44em; color:var(--ink2); font-size:14px; line-height:1.65; }
.co-ledgerhead { display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; }
.co-ver { font-family:ui-monospace,Consolas,monospace; font-size:11.5px; color:var(--accent);
  border:1px solid var(--ring); border-radius:999px; padding:3px 10px; letter-spacing:.04em; }
.co-install { margin-top:22px; background:#12141a; border-radius:12px; padding:16px 18px;
  overflow-x:auto; }
.co-install code { font-family:ui-monospace,Consolas,monospace; font-size:13px; color:#e6edf3;
  white-space:nowrap; }
.co-cta2 { text-align:center; padding:64px 0; border-top:1px solid var(--ring); }
.co-cta2 h2 { font-size:28px; font-weight:750; }
.co-cta2 p { color:var(--ink2); margin:12px auto 24px; max-width:36em; line-height:1.6; }
.co-foot { display:flex; gap:18px; padding:26px 0 40px; border-top:1px solid var(--ring);
  color:var(--muted); font-size:12.5px; flex-wrap:wrap; }
.co-foot .r { margin-left:auto; }
`;

const WHY = [
  ['#1', <>Every<br />Decision Proven</>,
   'Agents whose plans live on a graph, with provenance by construction. Any run replays byte for byte; when an agent lies, a set-containment check catches it before it acts.'],
  ['#2', <>Zero LLM Calls<br />At Inference</>,
   'The model thinks only at decision points; symbolic planning does the rest. Costs scale with decisions, not conversation length, and the result is benchmarked, not vibes.'],
  ['#3', <>An Adversarial<br />Proof Lab</>,
   'Six simulated customer stacks, each attacked with prompt-injected lies, tampered audit logs, and mid-run crashes. Failures are published with root causes, and every claim traces to a run on disk.'],
  ['#4', <>Real<br />Artifacts</>,
   'Replay a real run in the browser and download its trace. Nothing on our site is a mockup, and we label the one thing that is generated.'],
];

export function Company() {
  return (
    <div className="co">
      <style>{CSS}</style>
      <div className="co-wrap">
        <Nav links={NAV_LINKS} />

        <header className="co-hero">
          <div>
            <div className="co-eyebrow">Trustworthy agents · Verifiable self-improvement</div>
            <h1>AI you can prove.</h1>
            <p className="sub">
              Kyberos builds AI agents whose every decision is measured, traceable, and
              replayable, not trusted on faith, and works toward self-improvement that only
              counts evidence it can&apos;t fake.
            </p>
            <div className="co-cta">
              <a className="co-btn" href="/audit">Get a free agent audit</a>
              <a className="co-link" href="/design-partners">Become a design partner →</a>
              {/* A real route, not "#ledger": this page is a fixed-position
                  scroll container, so fragment navigation does not reliably
                  move it, and the product page is the better destination
                  anyway. */}
              <a className="co-link" href="/ledger">Install LEDGER →</a>
            </div>
            <div style={{ fontSize: 13, color: '#7c7d79', marginTop: 12, lineHeight: 1.55 }}>
              Send us your workflow, we&apos;ll attack it in our lab and send back a written
              report. No cost, no pitch.
            </div>
          </div>
          <div className="co-shot">
            <div className="bar"><i /><i /><i /></div>
            <GraphHero />
            <div className="co-cap">
              The core idea, animated: the agent plans across the action graph, prunes
              branches it cannot prove, and commits only verified steps. This one is an
              illustration, labeled per the house rule; the real artifacts, replay traces
              and provenance graphs, are on the&nbsp;
              <a href="/graph-agents" style={{ color: '#2b6cd4' }}>GATS page</a>.
            </div>
          </div>
        </header>

        <section className="co-sect">
          <h2>Unmeasured, untraceable AI fails in production.</h2>
          <p className="lead">
            Half of enterprise agent projects stall in pilot because nobody can govern,
            validate, or reproduce what the agent did. Observability tools score a black box
            after the fact. We think the fix is architectural: make the decision itself a
            first-class, inspectable artifact.
          </p>
        </section>

        <section className="co-sect" id="deadlines">
          <h2>Auditable agents are now a deadline, not a preference.</h2>
          <p className="lead">
            Two regulatory clocks turned &quot;deterministic and auditable&quot; into a budgeted
            requirement this year. Both describe, almost word for word, what GATS produces by
            construction.
          </p>
          <div className="co-grid">
            <div className="co-card">
              <div className="n">EU AI ACT · AUGUST 2, 2026</div>
              <h3>Article 12: log everything, or pay</h3>
              <p>
                High-risk obligations become broadly enforceable, requiring automatic event
                logging sufficient to trace a system&apos;s operation over its lifetime, with
                penalties up to €15M or 3% of worldwide turnover. GATS&apos;s provenance graph
                is that log, produced as a side effect of planning.
              </p>
            </div>
            <div className="co-card">
              <div className="n">FINRA · 2026 OVERSIGHT REPORT</div>
              <h3>Agents are now a supervisory risk category</h3>
              <p>
                FINRA names the risks plainly: multi-step reasoning that can&apos;t be audited,
                agents exceeding their intended scope, missing action trails and human
                checkpoints. Precondition verification and deterministic replay answer each
                one directly.
              </p>
            </div>
            <div className="co-card">
              <div className="n">THE EXAMINER&apos;S QUESTION</div>
              <h3>&quot;What did it do, and can you show me?&quot;</h3>
              <p>
                What did the agent access, when, under what authorization, and what decision
                did it influence? Session-level observability can&apos;t answer at that grain.
                Decision-level provenance can, and it replays byte for byte.
              </p>
            </div>
          </div>
        </section>

        <section className="co-sect" id="vendors">
          <h2>Selling an agent into a bank, an insurer, or a hospital?</h2>
          <p className="lead">
            Every enterprise security review asks the same question: how do we audit and
            reproduce what your agent did? Most vendors have no answer, and the deal stalls
            there. Kyberos is the answer you embed.
          </p>
          <div className="co-grid">
            <div className="co-card">
              <div className="n">EMBED</div>
              <h3>Keep your stack</h3>
              <p>
                GATS sits under the agent you already built as the planning-and-provenance
                layer. It complements LangGraph and CrewAI, it does not replace them.
              </p>
            </div>
            <div className="co-card">
              <div className="n">EVIDENCE</div>
              <h3>Answer procurement with artifacts</h3>
              <p>
                Every decision becomes a graph node with provenance by construction, and any
                run replays byte for byte, so &quot;show us what it did&quot; is a download,
                not a meeting.
              </p>
            </div>
            <div className="co-card">
              <div className="n">SPEED</div>
              <h3>Close the review, keep the deal</h3>
              <p>
                Your prospect already wrote the requirements: complete action trails, scope
                enforcement, reproducibility. You walk in with each one checked.
              </p>
            </div>
          </div>
          <div className="co-cta" style={{ marginTop: 26 }}>
            <a className="co-btn" href="/audit">Have us attack your agent, free</a>
            <a className="co-link" href="/graph-agents">Watch the deterministic replay →</a>
          </div>
        </section>

        <section className="co-sect" id="lab">
          <h2>The integration lab: proven, not promised.</h2>
          <p className="lead">
            We built six simulated customer stacks, a bank-dispute agent vendor, an HR
            screening platform, a broker-dealer supervision desk, an MSSP SOC, an insurance
            MGA, and a CPA firm, each as a completely separate system with its own ground
            truth and tool API. Then we embedded GATS under each one, attacked it with
            prompt-injected lies, tampered with its logs, crashed it mid-run, and audited
            the provenance graph. Every check passed:
          </p>
          <div className="co-stats">
            <div className="co-stat"><b>12 / 12</b><span>integration cases passed: 6 customer archetypes, 4 complex workflows (up to 19 steps), multi-tenant isolation, contract-drift detection</span></div>
            <div className="co-stat"><b>611 / 611</b><span>injected lies refused, tested from every execution prefix of every case, with zero false refusals</span></div>
            <div className="co-stat"><b>3,894 / 3,894</b><span>audit-log tamper attempts detected: every field of every record mutated, the hash chain broke every time</span></div>
            <div className="co-stat"><b>120 / 120</b><span>randomly generated customer systems solved with byte-identical plans, audit chains, and final states across reruns</span></div>
            <div className="co-stat"><b>114 / 114</b><span>mid-run crashes recovered by replaying the audit log, converging to the exact uninterrupted final state</span></div>
            <div className="co-stat"><b>60 / 60</b><span>provenance-graph corruptions caught by the independent validator; 549/549 why-provenance queries match brute-force ground truth</span></div>
          </div>
          <div className="co-fine">
            Simulated integration environments, stated plainly per the house rule. Every
            number reproduces from one deterministic command with zero LLM calls.{' '}
            <a href="/docs/integration-lab-report.pdf" style={{ color: '#2b6cd4' }}>Read the technical report (PDF) →</a>
          </div>
        </section>

        <section className="co-why">
          <h2>WHY KYBEROS?</h2>
          <div className="co-whygrid">
            {WHY.map(([n, h, p]) => (
              <div className="co-whycard" key={n}>
                <div className="wn">{n}</div>
                <h3>{h}</h3>
                <p>{p}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="co-sect" id="proof">
          <h2>GATS — the planning-and-provenance layer for agents</h2>
          <p className="lead">
            Our neuro-symbolic framework plans on a graph and calls the model only at decision
            points. It complements orchestration frameworks like LangGraph — it doesn&apos;t
            replace them — and it is benchmarked, not vibes:
          </p>
          <table className="co-bench">
            <thead>
              <tr><th>planner</th><th>main suite (100 tasks)</th><th>stress test (120 tasks)</th><th>LLM calls / task</th><th>variance across runs</th></tr>
            </thead>
            <tbody>
              <tr className="hl"><td><b>GATS (ours)</b></td><td><b>100%</b></td><td><b>100%</b></td><td><b>0 at inference</b></td><td><b>zero, deterministic</b></td></tr>
              <tr><td>LATS</td><td>92.0%</td><td>88.9%</td><td>~37</td><td>run-to-run drift</td></tr>
              <tr><td>ReAct</td><td>64.0%</td><td>23.9%</td><td>per-step</td><td>run-to-run drift</td></tr>
            </tbody>
          </table>
          <div className="co-fine">
            From our arXiv paper: a 100-task synthetic planning suite and a 12-scenario,
            120-task stress test. GATS holds 100% on both while the baselines degrade under
            stress. We say so plainly because that&apos;s the house rule. Real-workflow benchmarks with design
            partners are the current work item. <a href="/graph-agents" style={{ color: '#2b6cd4' }}>Full architecture →</a>
          </div>
        </section>

        <section className="co-sect" id="ledger">
          <div className="co-ledgerhead">
            <h2>LEDGER — the first thing we built on it, and you can run it today</h2>
            <span className="co-ver">v{VERSION}</span>
          </div>
          <p className="lead">
            A coding agent that can&apos;t lie about what it did. The planner is
            deterministic and the model never gets to mark its own work: every claim is
            checked by a sensor, every step is written to a hash-chained journal, and the
            whole episode replays bit-for-bit. When the agent&apos;s account of a step
            disagrees with what the instruments recorded, that contradiction is logged as
            an incident rather than smoothed over.
          </p>
          <div className="co-install">
            <code>{PIP_INSTALL}</code>
          </div>
          <div className="co-fine">
            Python 3.10+, no runtime dependencies. Works with Claude, OpenAI, and any
            OpenAI-compatible endpoint, including local models through Ollama.{' '}
            <a href="/ledger" style={{ color: '#2b6cd4' }}>Downloads and docs →</a>
          </div>
        </section>

        <section className="co-sect" id="rsi">
          <h2>Where it leads: self-improvement you can audit.</h2>
          <p className="lead">
            The same substrate answers the harder problem. A system that improves itself fails
            when its record of its own past becomes a story rather than a measurement, and each
            generation builds on the last one&apos;s unverified claims. GATS never lets a model
            mark its own work, which is the property self-improvement needs most. That program
            is research, and we label it that way: a world model that learns only from
            sensor-verified outcomes ships in LEDGER today, and training on those rewards does
            not exist yet.
          </p>
          <div className="co-cta" style={{ marginTop: 22 }}>
            <a className="co-link" href="/rsi">Read the RSI program →</a>
          </div>
        </section>

        <section className="co-sect">
          <h2>Adversarial testing is how we keep ourselves honest.</h2>
          <p className="lead">
            An agent that is never attacked has never been evaluated. So we attack ours:
            prompt-injected lies from every execution prefix, every field of every audit
            record mutated, crashes injected mid-run. Every claim on this site traces to a
            run on disk, and the cases that failed stay published with their root causes.
          </p>
          <div className="co-proof">
            <div className="co-proofcard">
              <h3>Traceable runs</h3>
              <p>Every number has a file behind it: the provenance graph, the hash-chained audit log, the replay trace, and the single command that reproduces it.</p>
            </div>
            <div className="co-proofcard">
              <h3>Published failures</h3>
              <p>Cases that failed stay up with their root causes. Comparing how confident a run looked with what it actually verified is how we catch an agent asserting something it never checked.</p>
            </div>
            <div className="co-proofcard">
              <h3>Try it yourself</h3>
              <p>Replay a real GATS run in your browser, step by step, and download the trace it produced.</p>
            </div>
          </div>
          <div className="co-cta" style={{ marginTop: 26 }}>
            <a className="co-link" href="/graph-agents">Replay a real run →</a>
            <a className="co-link" href="/audit">Have us attack your agent →</a>
          </div>
        </section>

        <section className="co-sect" id="demo">
          <h2>Drive a live agent.</h2>
          <p className="lead">
            The agent console is a working demo of the discipline, pointed at an everyday task
            so anyone can try it. It asks instead of guessing, shows its whole plan before it
            runs, and has an approval mode that stops before it acts. It&apos;s a demo, not a
            product, and it doesn&apos;t produce LEDGER receipts.
          </p>
          <div className="co-cta" style={{ marginTop: 22 }}>
            <a className="co-link" href="/agent">Open the live demo →</a>
          </div>
        </section>

        <section className="co-sect" id="about">
          <h2>Built by one founder, measured like a lab.</h2>
          <div className="co-founder">
            <div className="who">
              Kyberos is built by Maureese Williams — previously shipping production systems at
              Disney, Warner Bros Discovery, and Accenture, with a background across finance, now
              pursuing a second M.S. (PhD to follow) in Computer Science focused on AI/ML. An
              arXiv paper, a public experiment archive, and a working product stand in for the
              usual team page. Advisor bench forming now.
            </div>
          </div>
        </section>

        <section className="co-cta2">
          <h2>Deploying agents somewhere mistakes matter?</h2>
          <p>
            We&apos;re onboarding design partners in regulated and high-stakes workflows,
            teams that need to audit and reproduce every agent decision, and agent vendors
            who need to pass enterprise security review.
          </p>
          <div className="co-cta" style={{ justifyContent: 'center' }}>
            <a className="co-btn" href="/audit">Start with a free audit</a>
            <a className="co-link" href="/design-partners">Become a design partner →</a>
          </div>
        </section>

        <footer className="co-foot">
          <span>© 2026 Kyberos</span>
          <span><a href="/audit">Free audit</a></span>
          <span><a href="/rsi">RSI</a></span>
          <span><a href="/investors">Investors</a></span>
          <span className="r">AI you can prove.</span>
        </footer>
      </div>
    </div>
  );
}
