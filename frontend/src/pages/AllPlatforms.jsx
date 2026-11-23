import { useCallback, useEffect, useMemo, useState } from "react"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import AllChannels from "../components/AllChannels.jsx"
import AllStudio from "../components/AllStudio.jsx"
import HistoryTable, { groupRows } from "../components/HistoryTable.jsx"
import Nav from "../components/Nav.jsx"
import Step from "../components/Step.jsx"
import { PLATFORMS } from "../lib/all.js"

const empty = () => PLATFORMS.map((p) => ({ p, accounts: [], profiles: {} }))

// YouTube + LinkedIn + X on one screen: every account in one list, one video posted to the platforms you switch on, one history.
export default function AllPlatforms() {
  const [data, setData] = useState(empty)
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState([])
  const set = (kind, patch) => setData((cur) => cur.map((d) => (d.p.kind === kind ? { ...d, ...patch } : d)))

  const reload = useCallback(() => {
    PLATFORMS.forEach((p) => {  // a platform that fails to load just shows as empty; the others still work
      p.api.accounts().then((d) => set(p.kind, { accounts: d.accounts })).catch(() => {}).finally(() => setLoading(false))
      p.api.profiles().then((d) => set(p.kind, { profiles: Object.fromEntries(d.profiles.map((x) => [x.key, x])) })).catch(() => {})
    })
  }, [])
  const load = useCallback(() => {
    Promise.all(PLATFORMS.map((p) => p.api.history().then((d) => d.items).catch(() => []))).then((all) =>
      setItems(all.flat().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))))
  }, [])
  useEffect(() => { reload(); load() }, [reload, load])
  const groups = useMemo(() => groupRows(items), [items])

  return (
    <>
      <Nav />
      <header className="hero hero--li">
        <div className="hero-copy">
          <span className="eyebrow eyebrow--light">YouTube + LinkedIn + X</span>
          <h1 className="hero-title">Drop a video. <em>AI writes three posts.</em> One click to all.</h1>
          <p className="hero-sub">See every channel and profile in one place, review each post, and publish to the platforms you choose.</p>
        </div>
      </header>
      <div className="page stack">
        <Step n="1" title="All your channels and profiles"><AllChannels data={data} loading={loading} /></Step>
        <AllStudio data={data} onDone={load} />
        <section className="history">
          <div className="history-head"><Heading level={3}>History</Heading><Text size="sm" color="secondary">Posts made from this app on YouTube, LinkedIn and X. Edit or delete on each platform's own screen.</Text></div>
          <HistoryTable items={groups} />
        </section>
      </div>
    </>
  )
}
