import { useCallback, useEffect, useMemo, useState } from "react"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import HistoryTable, { groupRows } from "../components/HistoryTable.jsx"
import MetaStudio from "../components/MetaStudio.jsx"
import Nav from "../components/Nav.jsx"
import { fbCheck, fbHistory } from "../lib/api.js"

// The Meta screen: same flow as YouTube and LinkedIn (the local AI writes the post, you check it and press one button),
// and the history at the bottom.
export default function Facebook() {
  const [check, setCheck] = useState({ loading: true, error: "", data: null })
  const [items, setItems] = useState([])
  const groups = useMemo(() => groupRows(items), [items])
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
          <span className="eyebrow eyebrow--light">Meta</span>
          <h1 className="hero-title">Drop a video. <em>AI writes the post.</em> Facebook, Instagram and Threads.</h1>
          <p className="hero-sub">Your local model watches the video and writes the title, post text, caption and hashtags. Check it, and press Publish. Instagram posts as a Reel; Threads posts the same video once it has its own token.</p>
        </div>
      </header>
      <div className="page stack">
        <MetaStudio check={check} onCheck={runCheck} onDone={load} />
        <section className="history">
          <div className="history-head"><Heading level={3}>Meta history</Heading><Text size="sm" color="secondary">Updates every 10 seconds.</Text></div>
          <HistoryTable items={groups} />
        </section>
      </div>
    </>
  )
}
