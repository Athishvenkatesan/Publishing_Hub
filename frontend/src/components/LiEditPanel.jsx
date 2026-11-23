// Slide-in panel (not a popup) for editing the text of, or deleting, one post (LinkedIn or X; `api` and `site` come from the platform).
import { useEffect, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Heading } from "@astryxdesign/core/Heading"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { liDelete, liDetails, liUpdate } from "../lib/liApi.js"

const LI_API = { details: liDetails, update: liUpdate, del: liDelete }
import { TEXT_MAX } from "../lib/li.js"

export default function LiEditPanel({ panel, onClose, onDone, api = LI_API, site = "LinkedIn" }) {
  const { mode, row } = panel || {}
  const [text, setText] = useState("")
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  useEffect(() => {
    setErr("")
    if (!panel || mode !== "edit") return
    setLoading(true)
    api.details(row.id).then((x) => setText(x.text)).catch((e) => setErr(e.message)).finally(() => setLoading(false))
  }, [panel, mode, row?.id])

  async function run(fn, done) {
    setBusy(true); setErr("")
    try { await fn(); onDone(done) } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <>
      <div className={`scrim${panel ? " scrim--on" : ""}`} onClick={onClose} />
      <aside className={`drawer${panel ? " drawer--on" : ""}`} aria-hidden={!panel}>
        <header className="drawer-head">
          <div><Heading level={3}>{mode === "delete" ? `Delete from ${site}` : "Edit the post text"}</Heading>
            <Text size="sm" color="secondary">{row?.account_name}: {row?.title || row?.filename}</Text></div>
          <Button variant="secondary" size="sm" label="Close" onClick={onClose} />
        </header>
        {err && <Banner status="error" title="Could not complete" description={err} />}
        {loading && <div className="working"><Spinner /><Text size="sm">Loading the post...</Text></div>}
        {panel && mode === "edit" && !loading && (
          <div className="stack">
            <TextArea label="Post text" rows={12} value={text} onChange={setText} />
            <Text size="sm" color={text.length > TEXT_MAX ? "error" : "secondary"}>{text.length} / {TEXT_MAX}</Text>
            <Text size="sm" color="secondary">Only the text can change. {site} does not let apps swap the video or the audience.</Text>
            <Button label="Save changes" isLoading={busy} isDisabled={!text.trim() || text.length > TEXT_MAX || busy} onClick={() => run(() => api.update(row.id, { text }), `Post text updated on ${site}.`)} />
          </div>
        )}
        {panel && mode === "delete" && (
          <div className="stack">
            <Banner status="warning" title="This cannot be undone" description={`The post, its reactions and its comments are removed from ${site} for good.`} />
            <Button label="Delete permanently" isLoading={busy} isDisabled={busy} onClick={() => run(() => api.del(row.id), `Deleted from ${site}.`)} />
            <Button variant="secondary" label="Keep it" onClick={onClose} />
          </div>
        )}
      </aside>
    </>
  )
}
