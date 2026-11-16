export default function Hero({ items, accounts, onAccounts }) {
  const n = (s) => items.filter((i) => i.status === s).length
  const stats = [["Published", n("PUBLISHED")], ["Scheduled", n("SCHEDULED")], ["Failed", n("FAILED")], ["Channels", accounts.filter((a) => a.active).length]]
  return (
    <header className="hero">
      <div className="hero-copy">
        <span className="eyebrow eyebrow--light">DGM Publishing Hub</span>
        <h1 className="hero-title">Drop a video. <em>AI writes it.</em> You press go.</h1>
        <p className="hero-sub">Runs on your laptop's local model. Nothing is sent to an AI cloud.</p>
      </div>
      <div className="hero-side">
        <div className="stats">{stats.map(([k, v]) => <div key={k} className="stat"><b>{v}</b><span>{k}</span></div>)}</div>
        <button className="hero-btn" onClick={onAccounts}>Manage accounts</button>
      </div>
    </header>
  )
}
