import { SupabaseStatus } from '@/components/SupabaseStatus';

const capabilities = [
  {
    number: '01',
    title: 'Reconstruct',
    description: 'See how liquidity moved across every account.',
  },
  {
    number: '02',
    title: 'Forecast',
    description: 'Spot a cash crunch before it reaches your runway.',
  },
  {
    number: '03',
    title: 'Simulate',
    description: 'Model capital moves before you commit.',
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
          <a href="#how-it-works">How it works</a>
          <a href="#preview">The preview</a>
        </nav>

        <a className="header-cta" href="#preview">
          Explore the preview <span aria-hidden="true">↗</span>
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
            Reconstruct liquidity, see cash crunches coming, and test your next move
            before it matters.
          </p>

          <div className="hero-actions">
            <a className="button-primary" href="#preview">
              See the preview <span aria-hidden="true">↗</span>
            </a>
            <a className="button-secondary" href="#how-it-works">
              How it works <span aria-hidden="true">↓</span>
            </a>
          </div>

          <div className="hero-note">
            <span className="note-line" aria-hidden="true" />
            <p>Make your next move with the whole picture.</p>
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
              <small>Updated just now</small>
            </span>
          </div>

          <div className="dashboard-card">
            <div className="dashboard-topbar">
              <span className="dashboard-brand">
                <span className="mini-mark" aria-hidden="true">C</span>
                CashTrace
              </span>
              <span className="dashboard-period">Next 30 days <span aria-hidden="true">⌄</span></span>
            </div>

            <div className="dashboard-heading">
              <div>
                <p className="card-overline">Projected liquidity</p>
                <p className="balance">$2,840,500</p>
              </div>
              <span className="change-pill"><span aria-hidden="true">↗</span> 12.8%</span>
            </div>

            <div className="chart-wrap" aria-label="Projected liquidity trends upward over 30 days">
              <div className="chart-grid" aria-hidden="true">
                <span>$3.0m</span>
                <span>$2.5m</span>
                <span>$2.0m</span>
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
                <span>Today</span>
                <span>10 days</span>
                <span>20 days</span>
                <span>30 days</span>
              </div>
            </div>

            <div className="dashboard-bottom">
              <div className="account-summary">
                <span className="account-icon" aria-hidden="true">↗</span>
                <span><strong>Operating cash</strong><small>Across 4 accounts</small></span>
              </div>
              <span className="account-value">$1.26m</span>
            </div>
          </div>

          <div className="floating-label floating-label-bottom">
            <span className="label-icon label-icon-amber" aria-hidden="true">!</span>
            <span>
              <strong>Runway in view</strong>
              <small>Plan ahead with confidence</small>
            </span>
          </div>

          <span className="visual-caption">A clearer view of what comes next.</span>
        </div>
      </section>

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
