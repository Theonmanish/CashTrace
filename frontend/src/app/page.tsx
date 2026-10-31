import { CashTraceDashboard } from '@/components/CashTraceDashboard';
import { SupabaseStatus } from '@/components/SupabaseStatus';

const capabilities = [
  {
    number: '01',
    title: 'Reconstruct',
    description: 'See how liquidity moved across every settled transaction while isolating unpaid invoices.',
  },
  {
    number: '02',
    title: 'Forecast',
    description: 'Spot 7-day, 14-day, and 30-day cash crunches before they breach your safety reserve.',
  },
  {
    number: '03',
    title: 'Simulate',
    description: 'Model earlier collections, split supplier payouts, and reserve adjustments non-mutatingly.',
  },
];

export default function Home() {
  return (
    <main className="site-shell">
      <header className="site-header">
        <a className="wordmark" href="#home" aria-label="CashTrace home">
          <span className="wordmark-icon" aria-hidden="true">
            C
          </span>
          CashTrace
        </a>

        <nav className="header-nav" aria-label="Main navigation">
          <a href="#workspace">Live Analyzer</a>
          <a href="#how-it-works">How it works</a>
          <a href="#preview">The preview</a>
        </nav>

        <a className="header-cta" href="#workspace">
          Open Live Analyzer <span aria-hidden="true">↗</span>
        </a>
      </header>

      <section className="hero-section" id="home">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="eyebrow-dot" aria-hidden="true" />
            Hefty-Hacks 2026 <span className="eyebrow-divider">/</span> Finance × Trading
          </p>

          <h1>
            Cash flow,
            <br />
            without the
            <br />
            <span>blind spots.</span>
          </h1>

          <p className="hero-description">
            Reconstruct liquidity, detect MSME cash dead zones with transaction-backed root causes,
            and simulate your next move before it matters.
          </p>

          <div className="hero-actions">
            <a className="button-primary" href="#workspace">
              Launch Live Analyzer <span aria-hidden="true">↓</span>
            </a>
            <a className="button-secondary" href="#how-it-works">
              How it works <span aria-hidden="true">↓</span>
            </a>
          </div>

          <div className="hero-note">
            <span className="note-line" aria-hidden="true" />
            <p>Deterministic MSME Dead Zone Detection · Connected to FastAPI Engine.</p>
          </div>
        </div>

        <div className="hero-visual" id="preview" aria-label="CashTrace liquidity dashboard preview">
          <div className="visual-glow visual-glow-one" aria-hidden="true" />
          <div className="visual-glow visual-glow-two" aria-hidden="true" />
          <div className="orbit orbit-one" aria-hidden="true" />
          <div className="orbit orbit-two" aria-hidden="true" />

          <div className="floating-label floating-label-top">
            <span className="label-icon label-icon-green" aria-hidden="true">↗</span>
            <span>
              <strong>Cash outlook</strong>
              <small>7d / 14d / 30d horizons</small>
            </span>
          </div>

          <div className="dashboard-card">
            <div className="dashboard-topbar">
              <span className="dashboard-brand">
                <span className="mini-mark" aria-hidden="true">C</span>
                CashTrace MSME Engine
              </span>
              <span className="dashboard-period">Next 30 days <span aria-hidden="true">⌄</span></span>
            </div>

            <div className="dashboard-heading">
              <div>
                <p className="card-overline">Reconstructed Closing Cash</p>
                <p className="balance">₹1,62,000</p>
              </div>
              <span className="change-pill"><span aria-hidden="true">✓</span> Invariant OK</span>
            </div>

            <div className="chart-wrap" aria-label="Projected liquidity trends upward over 30 days">
              <div className="chart-grid" aria-hidden="true">
                <span>₹2.5L</span>
                <span>₹1.5L</span>
                <span>₹1.0L</span>
              </div>
              <svg
                className="liquidity-chart"
                viewBox="0 0 460 170"
                fill="none"
                role="img"
                aria-label="Liquidity forecast line chart"
              >
                <defs>
                  <linearGradient id="area-fill" x1="230" y1="28" x2="230" y2="170" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#51C99A" stopOpacity=".25" />
                    <stop offset="1" stopColor="#51C99A" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path
                  d="M0 125C29 118 36 94 68 101C100 108 104 73 137 80C169 87 180 104 211 86C242 68 253 72 283 58C313 44 322 67 351 48C380 29 389 41 414 26C432 15 443 22 460 10V170H0V125Z"
                  fill="url(#area-fill)"
                />
                <path
                  d="M0 125C29 118 36 94 68 101C100 108 104 73 137 80C169 87 180 104 211 86C242 68 253 72 283 58C313 44 322 67 351 48C380 29 389 41 414 26C432 15 443 22 460 10"
                  stroke="#27A879"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
                <circle cx="414" cy="26" r="6" fill="#fff" stroke="#27A879" strokeWidth="3" />
              </svg>
              <div className="chart-dates" aria-hidden="true">
                <span>As-Of</span>
                <span>7 days</span>
                <span>14 days</span>
                <span>30 days</span>
              </div>
            </div>

            <div className="dashboard-bottom">
              <div className="account-summary">
                <span className="account-icon" aria-hidden="true">↗</span>
                <span><strong>Safety Reserve Threshold</strong><small>Shree Precision Components</small></span>
              </div>
              <span className="account-value">₹1,00,000</span>
            </div>
          </div>

          <div className="floating-label floating-label-bottom">
            <span className="label-icon label-icon-amber" aria-hidden="true">!</span>
            <span>
              <strong>Dead Zones Detected</strong>
              <small>Simulate 1-click fixes below</small>
            </span>
          </div>

          <span className="visual-caption">Scroll down to interact with the live engine.</span>
        </div>
      </section>

      {/* Live Backend-Connected Workspace */}
      <CashTraceDashboard />

      <section className="capabilities-section" id="how-it-works" aria-label="What CashTrace helps you do">
        <div className="capabilities-intro">
          <p className="section-kicker">From blind spots to foresight</p>
          <h2>Know where you stand.<br />Decide where to go.</h2>
        </div>
        <div className="capability-list">
          {capabilities.map((capability) => (
            <article className="capability-card" key={capability.number}>
              <span className="capability-number">{capability.number}</span>
              <h3>{capability.title}</h3>
              <p>{capability.description}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="site-footer">
        <a className="wordmark footer-wordmark" href="#home">
          <span className="wordmark-icon" aria-hidden="true">C</span>
          CashTrace
        </a>
        <p>Financial dead zone detector <span aria-hidden="true">·</span> Hefty-Hacks 2026</p>
        <div className="integration-status"><SupabaseStatus /></div>
      </footer>
    </main>
  );
}
