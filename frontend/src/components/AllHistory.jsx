// The combined history with the same three-dot Action menu each platform's own screen has.
// YouTube: open, copy, edit, reschedule, visibility, remove, delete. LinkedIn: open, copy, edit, remove, delete. X: the same without edit.
// Meta (Facebook, Instagram, Threads) rows can open the post on each platform; their other actions are not built yet.
import { useMemo, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import { ytRemove, ytUpdate } from "../lib/api.js"
import { liDelete, liDetails, liRemove, liUpdate } from "../lib/liApi.js"
import { xDelete, xDetails, xRemove } from "../lib/xApi.js"
import HistoryTable, { groupRows } from "./HistoryTable.jsx"
import LiEditPanel from "./LiEditPanel.jsx"
import LiRowMenu from "./LiRowMenu.jsx"
import YtChannelAsk from "./YtChannelAsk.jsx"
import YtEditPanel from "./YtEditPanel.jsx"
import MetaRowMenu from "./MetaRowMenu.jsx"
import YtRowMenu from "./YtRowMenu.jsx"

const SITES = {
  linkedin: { name: "LinkedIn", canEdit: true, api: { details: liDetails, update: liUpdate, del: liDelete, remove: liRemove } },
  x: { name: "X", canEdit: false, api: { details: xDetails, update: null, del: xDelete, remove: xRemove } },
}
const META = ["facebook", "instagram-meta", "threads"]
const siteOf = (row) => (row.platform === "youtube-direct" ? "youtube" : row.platform)

export default function AllHistory({ items, onChanged }) {
  const groups = useMemo(() => groupRows(items), [items])
  const [note, setNote] = useState(null)
  const [panel, setPanel] = useState(null)   // { site, mode, row }
  const [ask, setAsk] = useState(null)       // an action waiting for a channel or account to be chosen
  const done = (text) => { setPanel(null); setNote({ status: "success", title: text }); onChanged() }

  async function act(kind, row) {
    setNote(null)
    if (row.rows?.length > 1) return setAsk({ kind, row })  // the same video is on several accounts: ask which one first
    if (kind === "open") return window.open(row.post_url, "_blank", "noopener")
    const site = siteOf(row), yt = site === "youtube"
    if (["edit", "delete"].includes(kind) || (yt && kind === "schedule")) return setPanel({ site, mode: kind, row })
    try {
      if (kind === "copy") { await navigator.clipboard.writeText(row.post_url); return setNote({ status: "success", title: "Link copied." }) }
      if (kind === "remove") await (yt ? ytRemove(row.id) : SITES[site].api.remove(row.id))
      else await ytUpdate(row.id, kind === "cancel" ? { cancel_schedule: true } : { privacy: kind })
      setNote({ status: "success", title: kind === "remove" ? "Removed from this list. The post on the platform is untouched."
        : kind === "cancel" ? "Schedule cancelled. The video stays private." : `Visibility set to ${kind}.` })
      onChanged()
    } catch (e) { setNote({ status: "error", title: "Could not complete", description: e.message }) }
  }

  const menu = (r) => {
    const site = siteOf(r)
    if (site === "youtube") return <YtRowMenu row={r} onAct={act} />
    if (SITES[site]) return <LiRowMenu row={r} onAct={act} site={SITES[site].name} canEdit={SITES[site].canEdit} />
    if (META.includes(r.platform)) return <MetaRowMenu row={r} />
    return <Button variant="secondary" size="sm" label="Actions" isDisabled />
  }
  const askSite = ask ? siteOf(ask.row.rows?.[0] || ask.row) : ""
  const li = panel && panel.site !== "youtube" ? SITES[panel.site] : null

  return (
    <section className="history">
      <div className="history-head"><Heading level={3}>History</Heading><Text size="sm" color="secondary">Posts made from this app. Use the Actions menu on a row. Facebook, Instagram and Threads rows can only open the post for now.</Text></div>
      {note && <Banner status={note.status} title={note.title} description={note.description} isDismissable onDismiss={() => setNote(null)} />}
      <HistoryTable items={groups} actions={menu} />
      <YtChannelAsk ask={ask} noun={askSite === "youtube" ? "channel" : "account"} onClose={() => setAsk(null)}
        labels={SITES[askSite] ? { open: `Open on ${SITES[askSite].name}`, edit: "Edit the post text", delete: `Delete from ${SITES[askSite].name}` } : {}}
        onPick={(r) => { const k = ask.kind; setAsk(null); act(k, r) }} />
      <YtEditPanel panel={panel?.site === "youtube" ? panel : null} onClose={() => setPanel(null)} onDone={done} />
      <LiEditPanel api={li?.api} site={li?.name} panel={li ? panel : null} onClose={() => setPanel(null)} onDone={done} />
    </section>
  )
}
