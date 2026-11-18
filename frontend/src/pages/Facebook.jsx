import { useCallback, useEffect, useState } from "react"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import FbCheck from "../components/FbCheck.jsx"
import FbPublish from "../components/FbPublish.jsx"
import HistoryTable from "../components/HistoryTable.jsx"
import Nav from "../components/Nav.jsx"
import { fbCheck, fbHistory } from "../lib/api.js"

const Step = ({ n, title, children }) => (
  <section className="step"><div className="step-head"><span className="step-n">{n}</span><Heading level={3}>{title}</Heading></div>{children}</section>
)

export default function Facebook() {
  const [check, setCheck] = useState({ loading: true, error: "", data: null })
  const [items, setItems] = useState([])
  const runCheck = useCallback(() => {
    setCheck((s) => ({ ...s, loading: true, error: "" }))
    fbCheck().then((data) => setCheck({ loading: false, error: "", data })).catch((e) => setCheck({ loading: false, error: e.message, data: null }))
  }, [])
  const load = useCallback(() => fbHistory().then((d) => setItems(d.items)).catch(() => {}), [])
  useEffect(() => { runCheck(); load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [runCheck, load])

  return (
    <>
      <Nav />
      <header className="hero hero--fb">
        <div className="hero-copy">
          <span className="eyebrow eyebrow--light">Facebook</span>
          <h1 className="hero-title">Check the token. <em>Then publish.</em></h1>
          <p className="hero-sub">Uses your Meta Graph API token from backend/.env. Instagram and WhatsApp are checked here but not wired yet.</p>
        </div>
      </header>
      <div className="page stack">
        <div className="grid grid--two">
          <Step n="1" title="What this token can do"><FbCheck state={check} onCheck={runCheck} /></Step>
          <Step n="2" title="Publish a video"><FbPublish pages={check.data?.pages || []} onDone={load} /></Step>
        </div>
        <section className="history">
          <div className="history-head"><Heading level={3}>Facebook history</Heading><Text size="sm" color="secondary">Updates every 10 seconds.</Text></div>
          <HistoryTable items={items} />
        </section>
      </div>
    </>
  )
}
