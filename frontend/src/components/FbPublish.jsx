// Publish one video to a Facebook Page: now, or scheduled 10 minutes to 75 days ahead.
import { useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { DateTimeInput } from "@astryxdesign/core/DateTimeInput"
import { FileInput } from "@astryxdesign/core/FileInput"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { TextInput } from "@astryxdesign/core/TextInput"
import { fbPublish } from "../lib/api.js"
import { TZ, localInZone } from "../lib/time.js"

export default function FbPublish({ pages, onDone }) {
  const postable = pages.filter((p) => p.tasks.includes("CREATE_CONTENT"))
  const [page, setPage] = useState("")
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState("")
  const [text, setText] = useState("")
  const [mode, setMode] = useState("now")
  const [when, setWhen] = useState(undefined)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const pageId = page || postable[0]?.id || ""

  const problem = !postable.length ? "Run the token check first. No Page you can post to yet."
    : !file ? "Choose a video." : mode === "schedule" && !when ? "Pick a date and time." : ""

  async function submit() {
    setBusy(true); setMsg(null)
    const f = new FormData()
    f.append("file", file); f.append("page_id", pageId); f.append("title", title); f.append("description", text)
    f.append("mode", mode); f.append("tz", TZ)
    if (mode === "schedule") f.append("scheduled_at", when.slice(0, 16))
    try {
      await fbPublish(f)
      setMsg({ status: "success", title: mode === "now" ? "Sent to Facebook" : "Scheduled on Facebook", description: "Track it in the history below." })
      setFile(null); setTitle(""); setText(""); setWhen(undefined); onDone()
    } catch (e) { setMsg({ status: "error", title: "Could not publish", description: e.message }) }
    finally { setBusy(false) }
  }

  return (
    <div className="stack">
      {msg && <Banner status={msg.status} title={msg.title} description={msg.description} isDismissable onDismiss={() => setMsg(null)} />}
      {postable.length > 1 && (
        <SegmentedControl label="Page" value={pageId} onChange={setPage}>
          {postable.map((p) => <SegmentedControlItem key={p.id} value={p.id} label={p.name} />)}
        </SegmentedControl>
      )}
      {postable.length === 1 && <Text size="sm">Posting to <b>{postable[0].name}</b></Text>}
      <FileInput label="Video" value={file} onChange={setFile} accept="video/mp4,video/quicktime" maxSize={300 * 1024 * 1024}
        description="MP4 or MOV, up to 300 MB." />
      <TextInput label="Title" isOptional value={title} onChange={setTitle} />
      <TextArea label="Description" isOptional rows={4} value={text} onChange={setText} />
      <SegmentedControl label="When" value={mode} onChange={setMode}>
        <SegmentedControlItem value="now" label="Publish now" />
        <SegmentedControlItem value="schedule" label="Schedule" />
      </SegmentedControl>
      {mode === "schedule" && (
        <div>
          <DateTimeInput label="Date and time" value={when} onChange={setWhen} min={localInZone(new Date(Date.now() + 11 * 60000))} hourFormat="24h" timeIncrement={5} />
          <Text size="sm" color="secondary">Time zone: {TZ}. Facebook needs 10 minutes to 75 days ahead.</Text>
        </div>
      )}
      <Button size="lg" label={mode === "now" ? "Publish to Facebook" : "Schedule on Facebook"} isLoading={busy} isDisabled={!!problem || busy} onClick={submit} />
      {problem && <Text size="sm" color="secondary">{problem}</Text>}
    </div>
  )
}
