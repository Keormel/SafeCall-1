const campaigns = [
  { id: "#17", name: "Bank impersonation", numbers: 19, complaints: 73, status: "Active", tone: "purple" },
  { id: "#16", name: "Delivery scam", numbers: 42, complaints: 58, status: "Active", tone: "orange" },
  { id: "#15", name: "Investment fraud", numbers: 31, complaints: 41, status: "Review", tone: "blue" },
  { id: "#14", name: "Prize notification", numbers: 12, complaints: 28, status: "Closed", tone: "green" },
];

function Icon({ name, size = 20 }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    phone: <><path d="M21 16.5v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 1.1 3.8 2 2 0 0 1 3.1 1.6h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L7 9.6a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.7 2Z" /></>,
    flag: <><path d="M5 21V4" /><path d="M5 4c5-3 8 3 14 0v10c-6 3-9-3-14 0" /></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    more: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
    trend: <><path d="m3 17 6-6 4 4 8-8" /><path d="M15 7h6v6" /></>,
  };

  return <svg aria-hidden="true" className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function MetricCard({ icon, label, value, change, color }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon ${color}`}><Icon name={icon} size={19} /></div>
      <div className="metric-copy"><p>{label}</p><strong>{value}</strong><span className="positive"><Icon name="trend" size={13} /> {change} <em>vs last month</em></span></div>
      <button className="icon-button" aria-label={`More options for ${label}`}><Icon name="more" size={19} /></button>
    </article>
  );
}

function ActivityChart() {
  const bars = [32, 49, 39, 62, 46, 70, 55, 76, 64, 82, 57, 91, 71, 84, 65, 78, 51, 67, 43, 60, 48, 73, 58, 69];
  return (
    <div className="chart-wrap">
      <div className="chart-y"><span>100</span><span>75</span><span>50</span><span>25</span><span>0</span></div>
      <div className="chart">
        <div className="chart-grid"><i /><i /><i /><i /><i /></div>
        <div className="bars">{bars.map((height, index) => <span key={index} style={{ height: `${height}%` }} className={index === 11 ? "selected" : ""} />)}</div>
        <div className="chart-x"><span>01 May</span><span>07 May</span><span>14 May</span><span>21 May</span><span>31 May</span></div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><span /></span><span>SafeCall</span><small>ADMIN</small></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          <a className="nav-item active" href="#overview"><Icon name="grid" /> Overview</a>
          <a className="nav-item" href="#numbers"><Icon name="phone" /> Phone numbers <b>1,248</b></a>
          <a className="nav-item" href="#complaints"><Icon name="flag" /> Complaints <b className="alert-count">12</b></a>
          <a className="nav-item" href="#campaigns"><Icon name="users" /> Campaigns</a>
        </nav>
        <div className="sidebar-bottom">
          <a className="nav-item" href="#settings"><span className="avatar">AK</span> Alex Kim <span className="chevron">⌄</span></a>
          <p className="version">SafeCall Admin <span>v1.0.0</span></p>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark"><span /></span> SafeCall</div>
          <div className="breadcrumb"><span>Workspace</span><b>/</b><strong>Overview</strong></div>
          <div className="top-actions">
            <button className="search-button" aria-label="Search"><Icon name="search" size={19} /><span>Search</span><kbd>⌘ K</kbd></button>
            <button className="notification-button" aria-label="Notifications"><Icon name="bell" size={20} /><i /></button>
            <div className="top-avatar">AK</div>
          </div>
        </header>

        <div className="content">
          <section className="page-heading">
            <div><h1>Good morning, Alex <span>✦</span></h1><p>Here&apos;s what&apos;s happening with your workspace today.</p></div>
            <button className="date-button">Last 30 days <span>⌄</span></button>
          </section>

          <section className="metrics" aria-label="Summary metrics">
            <MetricCard icon="phone" label="Total numbers" value="1,248" change="+8.2%" color="violet" />
            <MetricCard icon="flag" label="Total complaints" value="387" change="+12.4%" color="coral" />
            <MetricCard icon="users" label="Active campaigns" value="14" change="+2.1%" color="blue" />
            <article className="metric-card risk-card"><div className="metric-icon yellow">!</div><div className="metric-copy"><p>Avg. risk score</p><strong>72.4</strong><span className="warning">High risk <em>across all numbers</em></span></div><button className="icon-button" aria-label="More options for average risk score"><Icon name="more" size={19} /></button></article>
          </section>

          <section className="dashboard-grid">
            <article className="panel activity-panel">
              <div className="panel-heading"><div><h2>Complaint activity</h2><p>Reports received over time</p></div><div className="legend"><span /> Complaints <button className="icon-button"><Icon name="more" size={19} /></button></div></div>
              <ActivityChart />
            </article>
            <article className="panel distribution-panel">
              <div className="panel-heading"><div><h2>Risk distribution</h2><p>Numbers by risk level</p></div><button className="icon-button"><Icon name="more" size={19} /></button></div>
              <div className="donut-area"><div className="donut"><div><strong>1,248</strong><span>Numbers</span></div></div><div className="risk-legend"><span><i className="dot high" /> High <b>387</b></span><span><i className="dot medium" /> Medium <b>492</b></span><span><i className="dot low" /> Low <b>369</b></span></div></div>
            </article>
          </section>

          <section className="panel campaigns-panel" id="campaigns">
            <div className="panel-heading"><div><h2>Recent campaigns</h2><p>Monitor and manage detected campaigns</p></div><button className="link-button">View all <Icon name="arrow" size={16} /></button></div>
            <div className="table-scroll"><table><thead><tr><th>CAMPAIGN</th><th>TYPE</th><th>NUMBERS</th><th>COMPLAINTS</th><th>STATUS</th><th /></tr></thead><tbody>{campaigns.map((campaign) => <tr key={campaign.id}><td><span className={`campaign-icon ${campaign.tone}`}><Icon name="users" size={17} /></span><strong>Campaign {campaign.id}</strong></td><td>{campaign.name}</td><td>{campaign.numbers}</td><td>{campaign.complaints}</td><td><span className={`status ${campaign.status.toLowerCase()}`}><i />{campaign.status}</span></td><td><button className="row-more" aria-label={`More options for Campaign ${campaign.id}`}><Icon name="more" size={18} /></button></td></tr>)}</tbody></table></div>
          </section>

          <section className="panel campaign-detail" id="complaints">
            <div className="detail-heading"><div className="detail-title"><span className="campaign-icon purple"><Icon name="users" size={18} /></span><div><p>SELECTED CAMPAIGN</p><h2>Campaign #17 <span className="status active"><i /> Active</span></h2></div></div><button className="outline-button">Open campaign <Icon name="arrow" size={16} /></button></div>
            <div className="detail-grid"><div><span>TYPE</span><strong>Bank impersonation</strong></div><div><span>NUMBERS</span><strong>19</strong></div><div><span>COMPLAINTS</span><strong>73</strong></div><div className="number-list"><span>NUMBER PATTERNS</span><strong>+373 60 <i>XXX XXX</i></strong><strong>+373 68 <i>XXX XXX</i></strong><strong>+373 69 <i>XXX XXX</i></strong></div></div>
          </section>
          <footer>© 2024 SafeCall <span>·</span> Protecting people from unwanted calls</footer>
        </div>
      </main>
    </div>
  );
}
