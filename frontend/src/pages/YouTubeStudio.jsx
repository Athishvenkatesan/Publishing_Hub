import { useSearchParams } from "react-router"
import { Banner } from "@astryxdesign/core/Banner"
import { Link } from "react-router"
import Nav from "../components/Nav.jsx"
import StudioAccess from "../components/StudioAccess.jsx"
import StudioContent from "../components/StudioContent.jsx"
import StudioOverview from "../components/StudioOverview.jsx"
import StudioPlaylists from "../components/StudioPlaylists.jsx"
import StudioReports from "../components/StudioReports.jsx"
import YtAccounts from "../components/YtAccounts.jsx"
import { useYtAccount } from "../lib/useYtAccount.js"

const TABS = [["overview", "Overview"], ["content", "Content"], ["reports", "Reports"], ["playlists", "Playlists"], ["access", "Access"]]

export default function YouTubeStudio() {
  const [params, setParams] = useSearchParams()
  const { accounts, account, pick, ready } = useYtAccount()
  const tab = TABS.some(([k]) => k === params.get("tab")) ? params.get("tab") : "overview"
  const current = accounts.find((a) => a.key === account)
  const goto = (t) => setParams({ tab: t, ...(account ? { account } : {}) })
  const notice = params.get("connected") ? { status: "success", title: "Permission added", description: "The new permission is active for this account." }
    : params.get("error") ? { status: "error", title: "Sign-in failed", description: params.get("error") } : null
  const Tab = { overview: StudioOverview, content: StudioContent, reports: StudioReports, playlists: StudioPlaylists, access: StudioAccess }[tab]

  return (
    <>
      <Nav />
      <header className="hero hero--yt">
        <div className="hero-copy">
          <span className="eyebrow eyebrow--light">YouTube</span>
          <h1 className="hero-title">Studio management</h1>
          <p className="hero-sub">Your channel, videos and reports in one place, for the account you choose. {current ? `Showing ${current.label}.` : ""}</p>
        </div>
        <div className="hero-side"><Link className="hero-btn" to="/youtube">Back to YouTube</Link></div>
      </header>
      <div className="page stack">
        {notice && <Banner status={notice.status} title={notice.title} description={notice.description} isDismissable onDismiss={() => setParams({ tab, account }, { replace: true })} />}
        <section className="panel"><YtAccounts accounts={accounts} value={account} onChange={(k) => { pick(k); setParams({ tab, account: k }) }} /></section>
        <nav className="tabs" aria-label="Studio sections">
          {TABS.map(([k, name]) => <button key={k} type="button" className={`tab${tab === k ? " tab--on" : ""}`} onClick={() => goto(k)}>{name}</button>)}
        </nav>
        {ready && current && !current.connected && (
          <Banner status="warning" title="This account is not signed in" description="Open Manage accounts and press Connect for it, then come back." />
        )}
        {ready && current?.connected && <Tab account={account} goto={goto} />}
      </div>
    </>
  )
}
