import { useCallback, useEffect, useState } from "react"
import AllChannels from "../components/AllChannels.jsx"
import CheckAgain from "../components/CheckAgain.jsx"
import AllStudio from "../components/AllStudio.jsx"
import AllHistory from "../components/AllHistory.jsx"
import Nav from "../components/Nav.jsx"
import Step from "../components/Step.jsx"
import { PLATFORMS } from "../lib/all.js"

const empty = () => PLATFORMS.map((p) => ({ p, accounts: [], profiles: {} }))

// YouTube + LinkedIn + X + Meta on one screen: every account in one list, one video posted to the platforms you switch on, one history.
export default function AllPlatforms() {
  const [data, setData] = useState(empty)
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState([])
  const set = (kind, patch) => setData((cur) => cur.map((d) => (d.p.kind === kind ? { ...d, ...patch } : d)))

  const [checked, setChecked] = useState(null)
  const reload = useCallback(() => {  // asks every platform again; one that fails shows its reason and the others still load
    setLoading(true)
    return Promise.allSettled(PLATFORMS.map((p) => Promise.all([
      p.api.accounts().then((d) => set(p.kind, { accounts: d.accounts, error: "" })).catch((e) => set(p.kind, { accounts: [], error: e.message })),
      p.api.profiles().then((d) => set(p.kind, { profiles: Object.fromEntries(d.profiles.map((x) => [x.key, x])) })).catch(() => {}),
    ]))).finally(() => { setLoading(false); setChecked(new Date()) })
  }, [])
  const load = useCallback(() => {
    Promise.all(PLATFORMS.map((p) => p.api.history().then((d) => d.items).catch(() => []))).then((all) =>
      setItems(all.flat().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))))
  }, [])
  useEffect(() => { reload(); load() }, [reload, load])

  return (
    <>
      <Nav />
      <header className="hero hero--li">
        <div className="hero-copy">
          <span className="eyebrow eyebrow--light">All platforms</span>
          <h1 className="hero-title">Drop a video. <em>AI writes every post.</em> One click to all.</h1>
          <p className="hero-sub">YouTube, LinkedIn, X, Facebook, Instagram and Threads in one place. Review each post, and publish to the platforms you choose.</p>
        </div>
      </header>
      <div className="page stack">
        <Step n="1" title="All your channels and profiles" aside={<CheckAgain inline onCheck={() => { reload(); load() }} loading={loading} checked={checked} />}><AllChannels data={data} loading={loading} /></Step>
        <AllStudio data={data} onDone={load} />
        <AllHistory items={items} onChanged={load} />
      </div>
    </>
  )
}
