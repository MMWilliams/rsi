/**
 * Investors — /investors: the gated investor path. No fundraising language
 * on the public pages; this page collects an email and requests the brief
 * (Level 1: deck, one-pager, benchmark summary; Level 2 on diligence).
 */

import { useState } from 'react';
import { Nav } from './Nav.jsx';
import { NAV_LINKS } from './navLinks.js';

const CSS = `
.iv { --bg:#ffffff; --surface:#f6f6f4; --ink:#141518; --ink2:#45464a; --muted:#7c7d79;
  --ring:rgba(0,0,0,.12); --accent:#2b6cd4;
  background:var(--bg); color:var(--ink); position:fixed; inset:0; overflow-y:auto; overflow-x:hidden;
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif; -webkit-font-smoothing:antialiased; }
.iv * { box-sizing:border-box; margin:0; }
.iv a { color:inherit; text-decoration:none; }
.iv-wrap { max-width:760px; margin:0 auto; padding:0 24px 60px; }
.iv-hero { padding:64px 0 24px; }
.iv-eyebrow { font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--accent); font-weight:650; margin-bottom:14px; }
.iv-hero h1 { font-size:clamp(28px,4vw,42px); font-weight:750; letter-spacing:-.02em; }
.iv-hero p { color:var(--ink2); font-size:16px; line-height:1.65; margin-top:14px; }
.iv-facts { margin:26px 0; border:1px solid var(--ring); border-radius:14px; background:var(--surface); }
.iv-facts div { padding:14px 18px; border-bottom:1px solid rgba(0,0,0,.06); font-size:14px; color:var(--ink2); }
.iv-facts div:last-child { border-bottom:none; }
.iv-facts b { color:var(--ink); }
.iv-form { background:var(--surface); border:1px solid var(--ring); border-radius:16px; padding:24px; }
.iv-form label { display:block; font-size:13px; color:var(--ink2); margin:12px 0 6px; }
.iv-form input { width:100%; background:var(--bg); border:1px solid var(--ring); border-radius:10px;
  color:var(--ink); font-size:14px; padding:10px 13px; outline:none; }
.iv-form input:focus { border-color:var(--accent); }
.iv-btn { color:var(--accent); font-weight:650; font-size:14.5px;
  padding:12px 26px; border-radius:99px; cursor:pointer; margin-top:16px;
  background:#fff url('/assets/buttons/btn-ghost.webp') center/cover no-repeat;
  border:1px solid rgba(43,108,212,.40);
  box-shadow:0 2px 10px rgba(20,30,60,.06);
  transition:transform .15s, box-shadow .15s, border-color .15s; }
.iv-btn:hover { border-color:var(--accent); transform:translateY(-1px);
  box-shadow:0 6px 16px rgba(43,108,212,.18); }
.iv-fine { font-size:12px; color:var(--muted); margin-top:12px; line-height:1.55; }
.iv-foot { display:flex; gap:18px; padding:26px 0 40px; border-top:1px solid var(--ring);
  color:var(--muted); font-size:12.5px; margin-top:40px; }
.iv-foot .r { margin-left:auto; }
`;

export function Investors() {
  const [email, setEmail] = useState('');
  const [firm, setFirm] = useState('');
  const submit = (e) => {
    e.preventDefault();
    window.location.href =
      `mailto:maureese@kyberos.ai?subject=${encodeURIComponent('Kyberos investor brief — ' + (firm || email))}` +
      `&body=${encodeURIComponent(`Please send the investor brief.\n\nEmail: ${email}\nFirm: ${firm}`)}`;
  };
  return (
    <div className="iv">
      <style>{CSS}</style>
      <div className="iv-wrap">
        <Nav active="/investors" links={NAV_LINKS} />
        <header className="iv-hero">
          <div className="iv-eyebrow">Investor brief</div>
          <h1>Verifiable AI, with the receipts.</h1>
          <p>
            Kyberos is dedicated to two things and nothing else: trustworthy agents and
            verifiable recursive self-improvement. GATS, a neuro-symbolic agent framework with
            provenance by construction and deterministic replay, is proven in a public
            integration lab where every claim traces to an artifact, and it is the substrate
            our RSI research builds on. Request the brief for the deck, the papers, and the
            evidence galleries.
          </p>
        </header>

        <div className="iv-facts">
          <div><b>Category:</b> agent reliability / provenance — the layer that makes agents auditable.</div>
          <div><b>Benchmarked:</b> 100% task success vs LATS 88.9% / ReAct 23.9%; zero LLM calls at inference; zero run-to-run variance (our arXiv stress tests; real-workflow benchmarks in progress with design partners).</div>
          <div><b>Economics:</b> inference only at decision points — cost tracks decisions, not context length.</div>
          <div><b>Proof discipline:</b> a public integration lab — six adversarially attacked customer stacks, published failures with root causes, and disk-traceable claims.</div>
          <div><b>Wedge:</b> regulated and high-stakes agent deployments that must audit and reproduce every decision (EU AI Act enforcement from Aug 2026).</div>
          <div><b>Research:</b> verifiable self-improvement. A world model that learns only from sensor-verified outcomes ships today; training on those rewards is roadmap, not a result.</div>
        </div>

        <form className="iv-form" onSubmit={submit}>
          <label>Work email</label>
          <input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="you@fund.com" />
          <label>Firm</label>
          <input value={firm} onChange={e => setFirm(e.target.value)} placeholder="Fund / angel" />
          <button className="iv-btn" type="submit">Request the brief</button>
          <div className="iv-fine">
            Level 1 on request: deck, one-pager, benchmark summary. Deeper materials
            (technical deep-dive, traceable-run evidence, terms) follow on active diligence.
          </div>
        </form>

        <footer className="iv-foot">
          <span>© 2026 Kyberos</span>
          <span className="r">AI you can prove.</span>
        </footer>
      </div>
    </div>
  );
}
