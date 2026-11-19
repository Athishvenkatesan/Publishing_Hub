import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router"
import { Banner } from "@astryxdesign/core/Banner"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import HistoryTable from "../components/HistoryTable.jsx"
import Nav from "../components/Nav.jsx"
import YtEditPanel from "../components/YtEditPanel.jsx"
import YtRowMenu from "../components/YtRowMenu.jsx"
import YtStudio from "../components/YtStudio.jsx"
import { setYtAccount, ytAccounts, ytHistory, ytRemove, ytStatus, ytUpdate } from "../lib/api.js"

export default function YouTube() {
  const [params, setParams] = useSearchParams()
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState([])
  const [panel, setPanel] = useState(null)
  const [note, setNote] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [account, setAccount] = useState("")
  const notice = params.get("connected") ? { status: "success", title: "YouTube connected", description: "You can upload now." }
    : params.get("error") ? { status: "error", title: "YouTube sign-in failed", description: params.get("error") } : null

  const loadAccounts = useCallback(() => ytAccounts().then((d) => { setAccounts(d.accounts); return d }).catch(() => null), [])
  const pick = useCallback((key) => {
    setYtAccount(key); setAccount(key); setStatus(null)
    try { localStorage.setItem("ytAccount", key) } catch { /* a private window has no storage: the choice just is not remembered */ }
  }, [])
  const loadStatus = useCallback(() => {
    setLoading(true)
    ytStatus().then(setStatus).catch((e) => setStatus({ configured: true, connected: false, error: e.message })).finally(() => setLoading(false))
  }, [])
  const load = useCallback(() => ytHistory().then((d) => setItems(d.items)).catch(() => {}), [])
  const finished = (text) => { setPanel(null); setNote({ status: "success", title: text }); load() }
  async function act(kind, row) {
    setNote(null)
    if (["edit", "schedule", "delete"].includes(kind)) return setPanel({ mode: kind, row })
    try {
      if (kind === "copy") { await navigator.clipboard.writeText(row.post_url); return setNote({ status: "success", title: "Link copied." }) }
      if (kind === "remove") await ytRemove(row.id)
      else await ytUpdate(row.id, kind === "cancel" ? { cancel_schedule: true } : { privacy: kind })
      setNote({ status: "success", title: kind === "remove" ? "Removed from this list. The video on YouTube is untouched."
        : kind === "cancel" ? "Schedule cancelled. The video stays private." : `Visibility set to ${kind}.` })
      load()
    } catch (e) { setNote({ status: "error", title: "Could not complete", description: e.message }) }
  }
  // First load: choose the account (the one we just signed in, else the remembered one, else the first), then read the accounts again after any sign-in.
  useEffect(() => {
    loadAccounts().then((d) => {
      if (!d) return
      let saved = ""
      try { saved = localStorage.getItem("ytAccount") || "" } catch { /* no storage */ }
      const wanted = [params.get("account"), saved, d.default].find((k) => k && d.accounts.some((a) => a.key === k))
      pick(wanted || d.default)
    })
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (account) { loadStatus(); loadAccounts() } }, [account, loadStatus, loadAccounts])
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [load])
  useEffect(() => { if (notice) { const t = setTimeout(() => setParams({}, { replace: true }), 8000); return () => clearTimeout(t) } }, [notice, setParams])

  return (
    <>
      <Nav />
      <header className="hero hero--yt">
        <div className="hero-copy">
          <span className="eyebrow eyebrow--light">YouTube</span>
          <h1 className="hero-title">Drop a video. <em>AI writes it.</em> Straight to your channel.</h1>
          <p className="hero-sub">Your local model watches the video and writes the title, description, tags and more. Review, set advanced options, then upload now or schedule it.</p>
        </div>
      </header>
      <div className="page stack">
        <YtStudio status={status} loading={loading} notice={notice} reload={() => { loadStatus(); loadAccounts() }} onDone={load}
          accounts={accounts} account={account} onAccount={pick} />
        <section className="history">
          <div className="history-head"><Heading level={3}>YouTube history</Heading><Text size="sm" color="secondary">Updates every 10 seconds.</Text></div>
          {note && <Banner status={note.status} title={note.title} description={note.description} isDismissable onDismiss={() => setNote(null)} />}
          <HistoryTable items={items} actions={(r) => <YtRowMenu row={r} onAct={act} />} />
        </section>
        <YtEditPanel panel={panel} onClose={() => setPanel(null)} onDone={finished} />
      </div>
    </>
  )
}
