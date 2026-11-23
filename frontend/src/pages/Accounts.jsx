import { useState } from "react"
import { Link, useSearchParams } from "react-router"
import { Banner } from "@astryxdesign/core/Banner"
import MgrAccountCard from "../components/MgrAccountCard.jsx"
import MgrAddPanel from "../components/MgrAddPanel.jsx"
import MgrGuide from "../components/MgrGuide.jsx"
import Nav from "../components/Nav.jsx"
import { KINDS } from "../lib/mgrKinds.js"
import { useLoad } from "../lib/useLoad.js"

// The Accounts manager screen for one platform ("youtube" or "linkedin"): the accounts, what each is missing, and the setup guide.
export default function Accounts({ kind = "youtube" }) {
  const k = KINDS[kind]
  const [params, setParams] = useSearchParams()
  const { data, error, reload } = useLoad(k.list, [kind])
  const [panel, setPanel] = useState({ open: false, preset: "" })
  const [added, setAdded] = useState("")
  const accounts = data?.accounts || []
  const notice = params.get("connected") ? { status: "success", title: "Connected", description: "That account is signed in. Check the list below." }
    : params.get("error") ? { status: "error", title: "Sign-in failed", description: params.get("error") } : null

  return (
    <>
      <Nav />
      <header className={`hero ${k.heroClass}`}>
        <div className="hero-copy">
          <span className="eyebrow eyebrow--light">{k.name}</span>
          <h1 className="hero-title">{k.title}</h1>
          <p className="hero-sub">{k.sub}</p>
        </div>
        <div className="hero-side">
          <button type="button" className="hero-btn" onClick={() => setPanel({ open: true, preset: "" })}>Add account</button>
          <Link className="hero-btn" to={k.home}>Back to {k.name}</Link>
        </div>
      </header>
      <div className="page stack">
        {notice && <Banner status={notice.status} title={notice.title} description={notice.description} isDismissable onDismiss={() => setParams({}, { replace: true })} />}
        {added && <Banner status="success" title="Account added" description="Press Connect, or open Check setup to see what is left." isDismissable onDismiss={() => setAdded("")} />}
        {error && <Banner status="error" title="Could not load accounts" description={error} />}
        <div className="grid grid--two grid--mgr">
          <div className="stack">
            {accounts.map((a) => <MgrAccountCard key={a.key} kind={kind} acct={a} accounts={accounts} openCheck={a.key === added || params.get("account") === a.key}
              onChanged={reload} onReuse={(key) => setPanel({ open: true, preset: key })} />)}
            {data && !accounts.length && <p className="muted">No accounts yet. Press Add account.</p>}
          </div>
          {data && <MgrGuide kind={kind} guide={data.guide} redirectUri={data.redirect_uri} origin={data.js_origin} />}
        </div>
      </div>
      <MgrAddPanel kind={kind} open={panel.open} preset={panel.preset} accounts={accounts} origin={data?.js_origin || ""} redirectUri={data?.redirect_uri || ""} onClose={() => setPanel({ open: false, preset: "" })}
        onAdded={(a) => { setPanel({ open: false, preset: "" }); setAdded(a.key); reload() }} />
    </>
  )
}
