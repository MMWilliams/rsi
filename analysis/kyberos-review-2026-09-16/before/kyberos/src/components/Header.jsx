/**
 * Header — top bar with branding, live execution status, settings, and user menu.
 *
 * Location: src/components/Header.jsx
 */

import { useEffect, useRef, useState } from 'react';

import { Icon, Icons, T } from '../lib/theme';
import { useAuth } from '../auth/AuthProvider';
import { useMe } from '../account/MeProvider.jsx';

/**
 * @param {{
 *   onOpenSettings: () => void,
 *   onNewPlan: () => void,
 *   onToggleSidebar: () => void,
 *   sidebarOpen: boolean,
 *   connectionState: 'connected' | 'disconnected' | 'reconnecting',
 *   phase: string,
 *   health: { status?: string } | null,
 * }} props
 */
export function Header({
  onOpenSettings,
  onNewPlan,
  onToggleSidebar,
  sidebarOpen,
  connectionState,
  phase,
  health,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const { user, signIn, signOut } = useAuth();
  const { me } = useMe();

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDoc = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        background: 'rgba(250, 248, 245, 0.85)',
        backdropFilter: 'saturate(180%) blur(14px)',
        WebkitBackdropFilter: 'saturate(180%) blur(14px)',
        borderBottom: `1px solid ${T.border}`,
      }}
    >
      <div
        style={{
          maxWidth: 1280,
          margin: '0 auto',
          padding: '12px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        {/* Left: sidebar toggle + brand */}
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? 'Hide history' : 'Show history'}
          aria-pressed={sidebarOpen}
          className="kyb-icon-btn"
        >
          <Icon d={Icons.menu} size={18} color={T.text} />
        </button>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, minWidth: 0 }}>
          <span
            style={{
              fontFamily: T.fontDisplay,
              fontSize: 24,
              fontWeight: 900,
              letterSpacing: -0.5,
              color: T.ink,
            }}
          >
            Kyberos
          </span>
          <span
            style={{
              fontSize: 12,
              color: T.textMuted,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
            className="kyb-tagline"
          >
            the web, handled
          </span>
        </div>

        {/* Center: status pill */}
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <StatusPill connectionState={connectionState} phase={phase} health={health} />
        </div>

        {/* Right: actions */}
        <TierUsagePill me={me} />

        <button type="button" onClick={onNewPlan} className="kyb-new-plan">
          <Icon d={Icons.plus} size={14} color="#fff8ef" />
          <span className="kyb-hide-mobile">New plan</span>
        </button>

        <button
          type="button"
          onClick={onOpenSettings}
          aria-label="Settings"
          className="kyb-icon-btn"
        >
          <Icon d={Icons.settings} size={18} color={T.text} />
        </button>

        {user ? (
          <div ref={menuRef} style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="Account menu"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              style={{
                border: 'none',
                padding: 0,
                background: 'transparent',
                cursor: 'pointer',
                borderRadius: '50%',
              }}
            >
              <Avatar user={user} />
            </button>

            {menuOpen && (
              <div
                role="menu"
                style={{
                  position: 'absolute',
                  right: 0,
                  top: 'calc(100% + 8px)',
                  minWidth: 240,
                  background: T.surface,
                  borderRadius: 14,
                  border: `1px solid ${T.border}`,
                  boxShadow: T.shadowLift,
                  overflow: 'hidden',
                  zIndex: 60,
                }}
              >
                <div style={{ padding: '14px 16px', borderBottom: `1px solid ${T.border}` }}>
                  <div
                    style={{
                      fontWeight: 800,
                      fontSize: 14,
                      color: T.ink,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {user.displayName || 'Signed in'}
                  </div>
                  {user.email && (
                    <div
                      style={{
                        fontSize: 12,
                        color: T.textSoft,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        marginTop: 2,
                      }}
                    >
                      {user.email}
                    </div>
                  )}
                </div>

                <MenuItem
                  icon={Icons.settings}
                  onClick={() => {
                    setMenuOpen(false);
                    onOpenSettings();
                  }}
                >
                  Settings
                </MenuItem>

                <MenuItem
                  icon={Icons.logout}
                  tone="danger"
                  onClick={() => {
                    setMenuOpen(false);
                    signOut();
                  }}
                >
                  Sign out
                </MenuItem>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={signIn}
            className="kyb-sign-in"
            aria-label="Sign in with Google"
          >
            <span className="kyb-hide-mobile">Sign in</span>
            <Icon d={Icons.user || Icons.settings} size={16} color={T.text} />
          </button>
        )}
      </div>

      <style>{`
        .kyb-icon-btn {
          width: 38px;
          height: 38px;
          display: grid;
          place-items: center;
          border: 1px solid ${T.border};
          border-radius: 11px;
          background: ${T.surface};
          cursor: pointer;
          flex-shrink: 0;
        }
        .kyb-icon-btn:hover { background: ${T.surfaceWarm}; }
        .kyb-new-plan {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          padding: 9px 13px;
          background: ${T.accentDeep};
          color: #fff8ef;
          border: none;
          border-radius: 11px;
          font-weight: 800;
          font-size: 13px;
          cursor: pointer;
          font-family: ${T.font};
          flex-shrink: 0;
          box-shadow: 0 6px 18px rgba(92,65,43,0.20);
        }
        .kyb-new-plan:hover { filter: brightness(1.05); }
        @media (max-width: 640px) {
          .kyb-tagline { display: none; }
          .kyb-hide-mobile { display: none; }
          .kyb-new-plan { padding: 9px; }
        }
         .kyb-sign-in {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 9px 13px;
        background: ${T.surface};
        color: ${T.text};
        border: 1px solid ${T.borderStrong};
        border-radius: 11px;
        font-weight: 800;
        font-size: 13px;
        cursor: pointer;
        font-family: ${T.font};
        flex-shrink: 0;
      }
      .kyb-sign-in:hover { background: ${T.surfaceWarm}; }
      @media (max-width: 640px) {
        .kyb-sign-in { padding: 9px; }
      }
      `}</style>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Bits
// ---------------------------------------------------------------------------

/**
 * Compact tier + daily-usage indicator. Shows e.g. "Free · 12/100" or
 * "Ultimate · Unlimited". Turns warning-toned as the daily quota runs low.
 */
function TierUsagePill({ me }) {
  if (!me) return null;

  const usage = me.usage;
  const unlimited = usage?.unlimited;
  const remaining = usage?.remaining;

  let usageText = null;
  let tone = 'default';
  if (unlimited) {
    usageText = 'Unlimited';
  } else if (usage && typeof usage.used === 'number' && usage.limit != null) {
    usageText = `${usage.used}/${usage.limit}`;
    if (remaining === 0) tone = 'error';
    else if (typeof remaining === 'number' && remaining <= 10) tone = 'warning';
  }

  const toneBg =
    tone === 'error' ? T.errorSoft : tone === 'warning' ? T.warningSoft : T.surfaceAlt;
  const toneInk =
    tone === 'error' ? T.errorInk : tone === 'warning' ? T.warningInk : T.textSoft;
  const label = me.tier_label || 'Free';

  return (
    <div
      className="kyb-hide-mobile"
      title={
        unlimited
          ? `${label} · unlimited daily requests`
          : usageText
            ? `${label} · ${usageText} requests today`
            : label
      }
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 10px',
        borderRadius: 999,
        background: toneBg,
        border: `1px solid ${T.border}`,
        whiteSpace: 'nowrap',
      }}
    >
      <span style={{ fontSize: 12, fontWeight: 800, color: T.ink, letterSpacing: 0.2 }}>
        {label}
      </span>
      {usageText && (
        <>
          <span style={{ color: T.borderLight }}>·</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: toneInk }}>{usageText}</span>
        </>
      )}
    </div>
  );
}

function Avatar({ user }) {
  const initial = (user?.displayName || user?.email || '?').trim().charAt(0).toUpperCase();
  const photo = user?.photoURL;
  const size = 36;

  if (photo) {
    return (
      <img
        src={photo}
        alt={user?.displayName || 'User'}
        width={size}
        height={size}
        referrerPolicy="no-referrer"
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          objectFit: 'cover',
          border: `2px solid ${T.surface}`,
          boxShadow: T.shadowSoft,
        }}
      />
    );
  }

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: `linear-gradient(135deg, ${T.accentDeep}, ${T.accent})`,
        color: '#fff8ef',
        display: 'grid',
        placeItems: 'center',
        fontWeight: 900,
        fontSize: 14,
        boxShadow: T.shadowSoft,
        border: `2px solid ${T.surface}`,
      }}
    >
      {initial}
    </div>
  );
}

function MenuItem({ icon, children, onClick, tone }) {
  const danger = tone === 'danger';
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 16px',
        border: 'none',
        background: 'transparent',
        cursor: 'pointer',
        fontSize: 14,
        color: danger ? T.errorInk : T.text,
        textAlign: 'left',
        fontFamily: T.font,
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = T.surfaceAlt)}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
    >
      {icon && <Icon d={icon} size={15} color={danger ? T.error : T.textSoft} />}
      {children}
    </button>
  );
}

function StatusPill({ connectionState, phase, health }) {
  const cfg = (() => {
    if (connectionState === 'reconnecting') {
      return { color: T.warningInk, bg: T.warningSoft, dot: T.warning, label: 'Reconnecting' };
    }
    if (phase === 'streaming') {
      return { color: T.accentDeep, bg: '#fff3df', dot: T.accent, label: 'Planning' };
    }
    if (phase === 'approval') {
      return { color: T.accentDeep, bg: '#fff3df', dot: T.accent, label: 'Approval needed' };
    }
    if (phase === 'completed') {
      return { color: T.successInk, bg: T.successSoft, dot: T.success, label: 'Completed' };
    }
    if (phase === 'failed') {
      return { color: T.errorInk, bg: T.errorSoft, dot: T.error, label: 'Failed' };
    }
    if (health?.status === 'unreachable') {
      return { color: T.errorInk, bg: T.errorSoft, dot: T.error, label: 'Backend offline' };
    }
    if (health?.status === 'degraded') {
      return { color: T.warningInk, bg: T.warningSoft, dot: T.warning, label: 'Degraded' };
    }
    return { color: T.successInk, bg: T.successSoft, dot: T.success, label: 'Ready' };
  })();

  const pulsing = phase === 'streaming' || connectionState === 'reconnecting';

  return (
    <div
      role="status"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 12px',
        borderRadius: 999,
        background: cfg.bg,
        color: cfg.color,
        fontSize: 12,
        fontWeight: 700,
        border: `1px solid ${cfg.dot}33`,
      }}
    >
      <span
        aria-hidden
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: cfg.dot,
          animation: pulsing ? 'kyb-pulse 1.4s ease-in-out infinite' : 'none',
        }}
      />
      {cfg.label}
      <style>{`
        @keyframes kyb-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(1.3); }
        }
      `}</style>
    </div>
  );
}