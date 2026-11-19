import { useCallback, useEffect, useState } from "react"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import FbCheck from "../components/FbCheck.jsx"
import FbPhoto from "../components/FbPhoto.jsx"
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
          <span className="eyebrow eyebrow--light">Insta - Face - Threads</span>
          <h1 className="hero-title">Three channels. <em>One check.</em></h1>
          <p className="hero-sub">Uses your Meta token from backend/.env. Facebook can publish once the token has the right permission. Instagram, Threads and WhatsApp are checked here and not wired to send yet.</p>
        </div>
      </header>
      <div className="page stack">
        <div className="grid grid--two">
          <Step n="1" title="What your tokens can do"><FbCheck state={check} onCheck={runCheck} /></Step>
          <div className="stack">
            <Step n="2" title="Post a photo to Facebook"><FbPhoto pages={check.data?.pages || []} onDone={load} /></Step>
            <Step n="3" title="Publish a video to Facebook"><FbPublish pages={check.data?.pages || []} onDone={load} /></Step>
          </div>
        </div>
        <section className="history">
          <div className="history-head"><Heading level={3}>Facebook history</Heading><Text size="sm" color="secondary">Updates every 10 seconds.</Text></div>
          <HistoryTable items={items} />
        </section>
      </div>
    </>
  )
}
