// Publish one photo to a Facebook Page (JPG or PNG, up to 10 MB).
import { useEffect, useMemo, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { fbPublishPhoto } from "../lib/api.js"
import { TZ } from "../lib/time.js"
import FilePick from "./FilePick.jsx"
import FbPagePick, { postablePages } from "./FbPagePick.jsx"
import FbWhen from "./FbWhen.jsx"

export default function FbPhoto({ pages, onDone }) {
  const postable = postablePages(pages)
  const [page, setPage] = useState("")
  const [file, setFile] = useState(null)
  const [caption, setCaption] = useState("")
  const [mode, setMode] = useState("now")
  const [when, setWhen] = useState(undefined)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const pageId = page || postable[0]?.id || ""
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])

  const problem = !postable.length ? "Run the token check first. No Page you can post to yet."
    : !file ? "Choose an image." : mode === "schedule" && !when ? "Pick a date and time." : ""

  async function submit() {
    setBusy(true); setMsg(null)
    const f = new FormData()
    f.append("file", file); f.append("page_id", pageId); f.append("caption", caption); f.append("mode", mode); f.append("tz", TZ)
    if (mode === "schedule") f.append("scheduled_at", when.slice(0, 16))
    try {
      const d = await fbPublishPhoto(f)
      const url = d.items[0].post_url
      setMsg({ status: "success", title: mode === "now" ? "Photo posted to Facebook" : "Photo scheduled on Facebook",
        description: url ? url : "Track it in the history below." })
      setFile(null); setCaption(""); setWhen(undefined); onDone()
    } catch (e) { setMsg({ status: "error", title: "Could not post the photo", description: e.message }) }
    finally { setBusy(false) }
  }

  return (
    <div className="stack">
      {msg && <Banner status={msg.status} title={msg.title} description={msg.description} isDismissable onDismiss={() => setMsg(null)} />}
      <FbPagePick pages={pages} value={pageId} onChange={setPage} />
      <FilePick label="Image" value={file} onChange={setFile} accept="image/jpeg,image/png" maxMB={10}
        description="JPG or PNG, up to 10 MB." />
      {preview && <img className="preview preview--img" src={preview} alt="Selected" />}
      <TextArea label="Caption" isOptional rows={3} value={caption} onChange={setCaption} />
      <FbWhen mode={mode} setMode={setMode} when={when} setWhen={setWhen} />
      <Button size="lg" label={mode === "now" ? "Post photo to Facebook" : "Schedule photo on Facebook"} isLoading={busy} isDisabled={!!problem || busy} onClick={submit} />
      {problem && <Text size="sm" color="secondary">{problem}</Text>}
    </div>
  )
}
