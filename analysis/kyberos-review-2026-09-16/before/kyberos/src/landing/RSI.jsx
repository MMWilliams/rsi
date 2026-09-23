/**
 * RSI, /rsi: the research program. Per STRATEGY-2026.md the substrate is
 * shipped and RSI proper is research, and the page says which is which in
 * the same place it makes each claim (the house rule).
 */

import { Nav } from './Nav.jsx';
import { NAV_LINKS } from './navLinks.js';

const CSS = `
.rsi { --bg:#ffffff; --surface:#f6f6f4; --ink:#141518; --ink2:#45464a; --muted:#7c7d79;
  --ring:rgba(0,0,0,.12); --accent:#2b6cd4; --good:#0d7f0d;
  background:var(--bg); color:var(--ink); position:fixed; inset:0; overflow-y:auto; overflow-x:hidden;
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif; -webkit-font-smoothing:antialiased; }
.rsi * { box-sizing:border-box; margin:0; }
.rsi a { color:inherit; text-decoration:none; }
.rsi-wrap { max-width:1120px; margin:0 auto; padding:0 24px 60px; }
.rsi-hero { padding:60px 0 32px; max-width:48em; }
.rsi-eyebrow { font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--accent); font-weight:650; margin-bottom:14px; }
.rsi-hero h1 { font-size:clamp(30px,4.2vw,48px); line-height:1.07; font-weight:750; letter-spacing:-.02em; }
.rsi-hero p { color:var(--ink2); font-size:16.5px; line-height:1.65; margin-top:16px; }
.rsi-sect { padding:48px 0; border-top:1px solid var(--ring); }
.rsi-sect h2 { font-size:25px; font-weight:720; letter-spacing:-.01em; }
.rsi-sect .lead { color:var(--ink2); margin-top:10px; max-width:48em; line-height:1.65; }
.rsi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:16px; margin-top:26px; }
.rsi-card { background:var(--surface); border:1px solid var(--ring); border-radius:14px; padding:22px; }
.rsi-card .tag { display:inline-block; font-size:11px; font-weight:700; letter-spacing:.08em;
  border-radius:999px; padding:3px 10px; margin-bottom:12px; }
.rsi-card .tag.shipped { color:var(--good); background:rgba(13,127,13,.08); }
.rsi-card .tag.research { color:var(--accent); background:rgba(43,108,212,.08); }
.rsi-card .tag.built { color:#8a5a00; background:rgba(224,168,60,.14); }
.rsi-card h3 { font-size:15.5px; font-weight:650; margin-bottom:8px; }
.rsi-card p { font-size:13.5px; color:var(--ink2); line-height:1.62; }
.rsi-map { width:100%; border-collapse:collapse; margin-top:24px; font-size:14px; }
.rsi-map th { text-align:left; font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted);
  padding:9px 12px; border-bottom:1px solid var(--ring); }
.rsi-map td { padding:11px 12px; border-bottom:1px solid rgba(0,0,0,.06); color:var(--ink2); vertical-align:top; }
.rsi-map td b { color:var(--ink); }
.rsi-cta { display:flex; gap:14px; margin-top:26px; flex-wrap:wrap; align-items:center; }
.rsi-btn { display:inline-block; color:var(--accent); font-weight:650; font-size:14.5px;
  padding:12px 26px; border-radius:99px;
  background:#fff url('/assets/buttons/btn-ghost.webp') center/cover no-repeat;
  border:1px solid rgba(43,108,212,.40); box-shadow:0 2px 10px rgba(20,30,60,.06);
  transition:transform .15s, box-shadow .15s, border-color .15s; }
.rsi-btn:hover { border-color:var(--accent); transform:translateY(-1px); box-shadow:0 6px 16px rgba(43,108,212,.18); }
.rsi-link { color:var(--ink2); font-size:14px; border-bottom:1px solid var(--ring); padding-bottom:2px; }
.rsi-link:hover { color:var(--ink); }
.rsi-fine { font-size:12px; color:var(--muted); margin-top:12px; line-height:1.55; }
.rsi-foot { display:flex; gap:18px; padding:26px 0 40px; border-top:1px solid var(--ring);
  color:var(--muted); font-size:12.5px; }
.rsi-foot .r { margin-left:auto; }
`;

export function RSI() {
  return (
    <div className="rsi">
      <style>{CSS}</style>
      <div className="rsi-wrap">
        <Nav active="/rsi" links={NAV_LINKS} />

        <header className="rsi-hero">
          <div className="rsi-eyebrow">Research · Recursive self-improvement</div>
          <h1>A system that improves itself should only count evidence it can&apos;t fake.</h1>
          <p>
            Recursive self-improvement fails the same way a long-running agent does: its
            record of its own past becomes a story rather than a measurement. A system that
            grades its own progress finds the blind spots in its grader, and each generation
            builds on the last one&apos;s unverified claims. We think the fix is the one we
            already ship for agents: the system never marks its own work.
          </p>
        </header>

        <section className="rsi-sect">
          <h2>The thesis: the audit trail is the training loop.</h2>
          <p className="lead">
            GATS was built so an agent&apos;s every decision is measured, journaled and
            replayable. Those same parts are exactly what verifiable self-improvement needs,
            which is why this is where the verification work leads rather than a new line
            of business.
          </p>
          <table className="rsi-map">
            <thead>
              <tr><th>Self-improvement needs</th><th>What GATS gives it</th></tr>
            </thead>
            <tbody>
              <tr><td><b>A reward it can&apos;t game</b></td><td>Deterministic sensors. A claimed result counts only if an instrument observes it; a mismatch is logged as an incident, not scored.</td></tr>
              <tr><td><b>Somewhere safe to try things</b></td><td>Isolated worktrees per episode, so a failed attempt never touches the real system.</td></tr>
              <tr><td><b>An honest record of every attempt</b></td><td>A hash-chained journal of every decision, the full search table behind it, and what was predicted versus observed.</td></tr>
              <tr><td><b>A gate on every change to itself</b></td><td>Bit-exact replay, which exists today. The plan is to promote a learned change only if it replays every past run exactly; that gate is research.</td></tr>
            </tbody>
          </table>
        </section>

        <section className="rsi-sect">
          <h2>What exists today, and what&apos;s research.</h2>
          <p className="lead">
            Labelled per the house rule. <b>Shipped</b> is in the LEDGER release you can
            install. <b>Built</b> works and passes its tests but isn&apos;t released yet.{' '}
            <b>Research</b> isn&apos;t running, and we won&apos;t describe it as if it were.
          </p>
          <div className="rsi-grid">
            <div className="rsi-card">
              <span className="tag shipped">SHIPPED</span>
              <h3>A world model that learns only from evidence</h3>
              <p>
                LEDGER&apos;s planner learns what actions actually do in a specific codebase,
                and it learns from sensor-verified outcomes only, never from the model&apos;s
                account of what happened, so its picture of that codebase sharpens as it runs.
              </p>
            </div>
            <div className="rsi-card">
              <span className="tag built">BUILT</span>
              <h3>A refusal is never learned as a fact</h3>
              <p>
                When a human denies an action, the system routes around it for that session
                without teaching itself the action is useless. We found this one the hard
                way: the released version still learns it, and a single &quot;no&quot; can degrade every
                later run in that codebase. The fix is in the next release. A self-improving
                loop that can poison itself is the failure we exist to prevent.
              </p>
            </div>
            <div className="rsi-card">
              <span className="tag built">BUILT</span>
              <h3>Receipts that name the model</h3>
              <p>
                Every change carries a signed record of which model produced it, so when the
                system updates, the lineage of what it learned from stays inspectable.
              </p>
            </div>
            <div className="rsi-card">
              <span className="tag research">RESEARCH</span>
              <h3>Skills trained on sensor rewards</h3>
              <p>
                Reinforcement learning where the only reward is what the sensors observed, so
                the training signal inherits the same guarantee as the audit trail.
              </p>
            </div>
            <div className="rsi-card">
              <span className="tag research">RESEARCH</span>
              <h3>A planner that learns to search</h3>
              <p>
                Learned value and policy networks replacing the hand-set search rule, promoted
                only if they reproduce every recorded run exactly.
              </p>
            </div>
            <div className="rsi-card">
              <span className="tag research">RESEARCH</span>
              <h3>A learned model of consequences</h3>
              <p>
                An ensemble dynamics model replacing today&apos;s per-codebase statistics,
                trained on the trajectory store the journal already produces.
              </p>
            </div>
          </div>
          <div className="rsi-fine">
            Shipped items reproduce from the released LEDGER&apos;s test suite. Built items
            reproduce from the next release&apos;s. Research items are milestones on our
            roadmap, not results.
          </div>
        </section>

        <section className="rsi-sect">
          <h2>Working on self-improving systems that have to stay trustworthy?</h2>
          <p className="lead">
            We want to hear from labs and teams running agents that update themselves,
            where an unverified improvement is a risk rather than a win.
          </p>
          <div className="rsi-cta">
            <a className="rsi-btn" href="/design-partners">Talk to us</a>
            <a className="rsi-link" href="/ledger">See the substrate in LEDGER →</a>
            <a className="rsi-link" href="/graph-agents">How GATS works →</a>
          </div>
        </section>

        <footer className="rsi-foot">
          <span>© 2026 Kyberos</span>
          <span className="r">AI you can prove.</span>
        </footer>
      </div>
    </div>
  );
}
