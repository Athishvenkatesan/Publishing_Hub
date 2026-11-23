import { useCallback, useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router"
import { Banner } from "@astryxdesign/core/Banner"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import HistoryTable, { groupRows } from "../components/HistoryTable.jsx"
import LiEditPanel from "../components/LiEditPanel.jsx"
import LiRowMenu from "../components/LiRowMenu.jsx"
import PostStudio from "../components/PostStudio.jsx"
import Nav from "../components/Nav.jsx"
import YtChannelAsk from "../components/YtChannelAsk.jsx"

// The LinkedIn or X posting screen (`p` from lib/platforms.js): the studio on top, the history with its three-dot menu below.
export default function PostPage({ p }) {
  const [params, setParams] = useSearchParams()
  const [accounts, setAccounts] = useState([])
  const [redirectUri, setRedirectUri] = useState("")
  const [profiles, setProfiles] = useState({})
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState([])
  const [panel, setPanel] = useState(null)
  const [ask, setAsk] = useState(null)   // an action waiting for an account to be chosen
  const [note, setNote] = useState(null)
  const groups = useMemo(() => groupRows(items), [items])
  const notice = params.get("connected") ? { status: "success", title: `${p.name} connected`, description: "You can post now." }
    : params.get("error") ? { status: "error", title: `${p.name} sign-in failed`, description: params.get("error") } : null

  const load = useCallback(() => p.api.history().then((d) => setItems(d.items)).catch(() => {}), [p])
  const reload = useCallback(() => {
    p.api.accounts().then((d) => { setAccounts(d.accounts); setRedirectUri(d.redirect_uri || "") }).catch(() => {}).finally(() => setLoading(false))
    p.api.profiles().then((d) => setProfiles(Object.fromEntries(d.profiles.map((p) => [p.key, p])))).catch(() => {})
  }, [p])
  useEffect(() => { reload(); load() }, [reload, load])
  useEffect(() => { if (notice) { const t = setTimeout(() => setParams({}, { replace: true }), 8000); return () => clearTimeout(t) } }, [notice, setParams])

  const finished = (text) => { setPanel(null); setNote({ status: "success", title: text }); load() }
  async function act(kind, row) {
    setNote(null)
    if (row.rows?.length > 1) return setAsk({ kind, row })  // the same video is on several accounts: ask which one first
    if (kind === "open") return window.open(row.post_url, "_blank", "noopener")
    if (kind === "edit" || kind === "delete") return setPanel({ mode: kind, row })
    try {
      if (kind === "copy") { await navigator.clipboard.writeText(row.post_url); return setNote({ status: "success", title: "Link copied." }) }
      await p.api.remove(row.id)
      setNote({ status: "success", title: `Removed from this list. The post on ${p.name} is untouched.` }); load()
    } catch (e) { setNote({ status: "error", title: "Could not complete", description: e.message }) }
  }

  return (
    <>
      <Nav />
      <header className={`hero ${p.heroClass}`}>
        <div className="hero-copy">
          <span className="eyebrow eyebrow--light">{p.name}</span>
          <h1 className="hero-title">{p.hero.lead} <em>{p.hero.em}</em> {p.hero.tail}</h1>
          <p className="hero-sub">{p.hero.sub}</p>
        </div>
      </header>
      <div className="page stack">
        <PostStudio p={p} accounts={accounts} profiles={profiles} redirectUri={redirectUri} notice={notice} loading={loading} reload={reload} onDone={load} />
        <section className="history">
          <div className="history-head"><Heading level={3}>{p.name} history</Heading><Text size="sm" color="secondary">Posts made from this app.</Text></div>
          {note && <Banner status={note.status} title={note.title} description={note.description} isDismissable onDismiss={() => setNote(null)} />}
          <HistoryTable items={groups} actions={(r) => <LiRowMenu row={r} onAct={act} site={p.name} canEdit={p.canEdit} />} />
        </section>
        <LiEditPanel api={p.api} site={p.name} panel={panel} onClose={() => setPanel(null)} onDone={finished} />
        <YtChannelAsk ask={ask} noun="account" labels={{ open: `Open on ${p.name}`, edit: "Edit the post text", delete: `Delete from ${p.name}` }} onClose={() => setAsk(null)} onPick={(r) => { const k = ask.kind; setAsk(null); act(k, r) }} />
      </div>
    </>
  )
}
