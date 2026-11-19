// Slide-in panel (not a popup) for editing, rescheduling or deleting one YouTube upload.
import { useEffect, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { DateTimeInput } from "@astryxdesign/core/DateTimeInput"
import { Heading } from "@astryxdesign/core/Heading"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { TextInput } from "@astryxdesign/core/TextInput"
import { ytDelete, ytDetails, ytUpdate } from "../lib/api.js"
import { TZ, localInZone } from "../lib/time.js"

const TITLES = { edit: "Edit details", schedule: "Reschedule", delete: "Delete from YouTube" }

export default function YtEditPanel({ panel, onClose, onDone }) {
  const { mode, row } = panel || {}
  const [d, setD] = useState({ title: "", description: "", tags: "" })
  const [when, setWhen] = useState(undefined)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  useEffect(() => {
    setErr(""); setWhen(undefined)
    if (!panel || mode === "delete") return
    setLoading(true)
    ytDetails(row.id).then((x) => setD({ title: x.title, description: x.description, tags: x.tags })).catch((e) => setErr(e.message)).finally(() => setLoading(false))
  }, [panel, mode, row?.id])

  async function run(fn, done) {
    setBusy(true); setErr("")
    try { await fn(); onDone(done) } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const save = () => run(() => ytUpdate(row.id, d), "Details updated on YouTube.")
  const reschedule = () => run(() => ytUpdate(row.id, { scheduled_at: when.slice(0, 16), tz: TZ }), "Rescheduled on YouTube.")
  const remove = () => run(() => ytDelete(row.id), "Deleted from YouTube.")

  return (
    <>
      <div className={`scrim${panel ? " scrim--on" : ""}`} onClick={onClose} />
      <aside className={`drawer${panel ? " drawer--on" : ""}`} aria-hidden={!panel}>
        <header className="drawer-head">
          <div><Heading level={3}>{TITLES[mode] || ""}</Heading>
            <Text size="sm" color="secondary">{row?.title || row?.filename}</Text></div>
          <Button variant="secondary" size="sm" label="Close" onClick={onClose} />
        </header>
        {err && <Banner status="error" title="Could not complete" description={err} />}
        {loading && <div className="working"><Spinner /><Text size="sm">Reading the video from YouTube...</Text></div>}
        {panel && mode === "edit" && !loading && (
          <div className="stack">
            <TextInput label="Title" isRequired value={d.title} onChange={(v) => setD({ ...d, title: v })} />
            <Text size="sm" color={d.title.length > 100 ? "error" : "secondary"}>{d.title.length} / 100</Text>
            <TextArea label="Description" rows={10} value={d.description} onChange={(v) => setD({ ...d, description: v })} />
            <TextInput label="Tags" value={d.tags} onChange={(v) => setD({ ...d, tags: v })} placeholder="water, dubai" />
            <Button label="Save changes" isLoading={busy} isDisabled={!d.title.trim() || d.title.length > 100 || busy} onClick={save} />
          </div>
        )}
        {panel && mode === "schedule" && !loading && (
          <div className="stack">
            <DateTimeInput label="New date and time" value={when} onChange={setWhen} min={localInZone(new Date(Date.now() + 11 * 60000))} hourFormat="24h" timeIncrement={5} />
            <Text size="sm" color="secondary">Time zone: {TZ}. The video stays private and YouTube makes it public at that time.</Text>
            <Button label="Save new time" isLoading={busy} isDisabled={!when || busy} onClick={reschedule} />
          </div>
        )}
        {panel && mode === "delete" && (
          <div className="stack">
            <Banner status="warning" title="This cannot be undone"
              description="The video, its views and its comments are removed from your YouTube channel for good." />
            <Button label="Delete permanently" isLoading={busy} isDisabled={busy} onClick={remove} />
            <Button variant="secondary" label="Keep it" onClick={onClose} />
          </div>
        )}
      </aside>
    </>
  )
}
