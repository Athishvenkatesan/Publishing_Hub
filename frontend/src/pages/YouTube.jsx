import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import HistoryTable from "../components/HistoryTable.jsx"
import Nav from "../components/Nav.jsx"
import YtConnect from "../components/YtConnect.jsx"
import YtPublish from "../components/YtPublish.jsx"
import { ytHistory, ytStatus } from "../lib/api.js"

const Step = ({ n, title, children }) => (
  <section className="step"><div className="step-head"><span className="step-n">{n}</span><Heading level={3}>{title}</Heading></div>{children}</section>
)

export default function YouTube() {
  const [params, setParams] = useSearchParams()
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState([])
  const notice = params.get("connected") ? { status: "success", title: "YouTube connected", description: "You can upload now." }
    : params.get("error") ? { status: "error", title: "YouTube sign-in failed", description: params.get("error") } : null

  const loadStatus = useCallback(() => {
    setLoading(true)
    ytStatus().then(setStatus).catch((e) => setStatus({ configured: true, connected: false, error: e.message })).finally(() => setLoading(false))
  }, [])
  const load = useCallback(() => ytHistory().then((d) => setItems(d.items)).catch(() => {}), [])
  useEffect(() => { loadStatus(); load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [loadStatus, load])
  useEffect(() => { if (notice) { const t = setTimeout(() => setParams({}, { replace: true }), 8000); return () => clearTimeout(t) } }, [notice, setParams])

  return (
    <>
      <Nav />
      <header className="hero hero--yt">
        <div className="hero-copy">
          <span className="eyebrow eyebrow--light">YouTube</span>
          <h1 className="hero-title">Straight to <em>your channel.</em></h1>
          <p className="hero-sub">Signs in with your own Google app. Upload a video now, or schedule it and YouTube publishes it at that time.</p>
        </div>
      </header>
      <div className="page stack">
        <div className="grid grid--two">
          <Step n="1" title="Your channel"><YtConnect status={status} loading={loading} notice={notice} reload={loadStatus} /></Step>
          <Step n="2" title="Upload a video"><YtPublish connected={!!status?.connected && !status?.error} onDone={load} /></Step>
        </div>
        <section className="history">
          <div className="history-head"><Heading level={3}>YouTube history</Heading><Text size="sm" color="secondary">Updates every 10 seconds.</Text></div>
          <HistoryTable items={items} />
        </section>
      </div>
    </>
  )
}
