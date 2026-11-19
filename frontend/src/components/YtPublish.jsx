// Upload one video to the connected YouTube channel, now or scheduled (YouTube publishes it at that time).
import { useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { TextInput } from "@astryxdesign/core/TextInput"
import { ytPublish } from "../lib/api.js"
import { TZ } from "../lib/time.js"
import FbWhen from "./FbWhen.jsx"
import FilePick from "./FilePick.jsx"

export default function YtPublish({ connected, onDone }) {
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState("")
  const [text, setText] = useState("")
  const [tags, setTags] = useState("")
  const [privacy, setPrivacy] = useState("public")
  const [mode, setMode] = useState("now")
  const [when, setWhen] = useState(undefined)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const problem = !connected ? "Connect YouTube first." : !file ? "Choose a video." : !title.trim() ? "YouTube needs a title."
    : title.length > 100 ? "Title is over 100 characters." : mode === "schedule" && !when ? "Pick a date and time." : ""

  async function submit() {
    setBusy(true); setMsg(null)
    const f = new FormData()
    f.append("file", file); f.append("title", title); f.append("description", text); f.append("tags", tags)
    f.append("privacy", privacy); f.append("mode", mode); f.append("tz", TZ)
    if (mode === "schedule") f.append("scheduled_at", when.slice(0, 16))
    try {
      await ytPublish(f)
      setMsg({ status: "success", title: mode === "now" ? "Uploaded to YouTube" : "Scheduled on YouTube",
        description: "YouTube is processing it. Track it in the history below." })
      setFile(null); setTitle(""); setText(""); setTags(""); setWhen(undefined); onDone()
    } catch (e) { setMsg({ status: "error", title: "Could not upload", description: e.message }) }
    finally { setBusy(false) }
  }

  return (
    <div className="stack">
      {msg && <Banner status={msg.status} title={msg.title} description={msg.description} isDismissable onDismiss={() => setMsg(null)} />}
      <FilePick label="Video" value={file} onChange={setFile} accept="video/mp4,video/quicktime" maxMB={300} description="MP4 or MOV, up to 300 MB." />
      <TextInput label="Title" isRequired value={title} onChange={setTitle} />
      <Text size="sm" color={title.length > 100 ? "error" : "secondary"}>{title.length} / 100</Text>
      <TextArea label="Description" isOptional rows={4} value={text} onChange={setText} />
      <TextInput label="Tags" isOptional value={tags} onChange={setTags} placeholder="dubai, water, saving" />
      {mode === "now" && (
        <SegmentedControl label="Who can watch" value={privacy} onChange={setPrivacy}>
          <SegmentedControlItem value="public" label="Public" />
          <SegmentedControlItem value="unlisted" label="Unlisted" />
          <SegmentedControlItem value="private" label="Private" />
        </SegmentedControl>
      )}
      <FbWhen mode={mode} setMode={setMode} when={when} setWhen={setWhen}
        note="The video uploads now as private, and YouTube makes it public at that time." />
      <Button size="lg" label={mode === "now" ? "Upload to YouTube" : "Schedule on YouTube"} isLoading={busy} isDisabled={!!problem || busy} onClick={submit} />
      {problem && <Text size="sm" color="secondary">{problem}</Text>}
      {busy && <Text size="sm" color="secondary">Uploading to YouTube. A large video can take a few minutes.</Text>}
    </div>
  )
}
