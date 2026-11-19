// Publish one video to a Facebook Page.
import { useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { TextInput } from "@astryxdesign/core/TextInput"
import { fbPublish } from "../lib/api.js"
import { TZ } from "../lib/time.js"
import FilePick from "./FilePick.jsx"
import FbPagePick, { postablePages } from "./FbPagePick.jsx"
import FbWhen from "./FbWhen.jsx"

export default function FbPublish({ pages, onDone }) {
  const postable = postablePages(pages)
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
      setMsg({ status: "success", title: mode === "now" ? "Video sent to Facebook" : "Video scheduled on Facebook", description: "Track it in the history below." })
      setFile(null); setTitle(""); setText(""); setWhen(undefined); onDone()
    } catch (e) { setMsg({ status: "error", title: "Could not publish", description: e.message }) }
    finally { setBusy(false) }
  }

  return (
    <div className="stack">
      {msg && <Banner status={msg.status} title={msg.title} description={msg.description} isDismissable onDismiss={() => setMsg(null)} />}
      <FbPagePick pages={pages} value={pageId} onChange={setPage} />
      <FilePick label="Video" value={file} onChange={setFile} accept="video/mp4,video/quicktime" maxMB={300}
        description="MP4 or MOV, up to 300 MB." />
      <TextInput label="Title" isOptional value={title} onChange={setTitle} />
      <TextArea label="Description" isOptional rows={4} value={text} onChange={setText} />
      <FbWhen mode={mode} setMode={setMode} when={when} setWhen={setWhen} />
      <Button size="lg" label={mode === "now" ? "Publish video to Facebook" : "Schedule video on Facebook"} isLoading={busy} isDisabled={!!problem || busy} onClick={submit} />
      {problem && <Text size="sm" color="secondary">{problem}</Text>}
    </div>
  )
}
