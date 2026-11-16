import { useEffect, useMemo, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Heading } from "@astryxdesign/core/Heading"
import { analyzeStatus, analyzeVideo, createPost } from "../lib/api.js"
import { LIMITS, emptyCopy, fromAi, toPayload } from "../lib/copy.js"
import { TZ } from "../lib/time.js"
import PostPreview from "./PostPreview.jsx"
import CopyEditor from "./CopyEditor.jsx"
import UploadStep from "./UploadStep.jsx"
import WhenStep from "./WhenStep.jsx"

const Step = ({ n, title, children, dim }) => (
  <section className={`step${dim ? " step--dim" : ""}`}>
    <div className="step-head"><span className="step-n">{n}</span><Heading level={3}>{title}</Heading></div>
    {children}
  </section>
)

export default function PublishForm({ onDone, accounts }) {
  const [picked, setPicked] = useState([])
  const [file, setFile] = useState(null)
  const [lang, setLang] = useState("en")
  const [hint, setHint] = useState("")
  const [copy, setCopy] = useState(emptyCopy())
  const [ai, setAi] = useState({ state: "idle", reason: "" })
  const [found, setFound] = useState(null)
  const [mode, setMode] = useState("now")
  const [when, setWhen] = useState(undefined)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    analyzeStatus().then((s) => !s.ready && setAi({ state: "off", reason: `${s.reason} The text fields still work: write them yourself.` })).catch(() => {})
  }, [])

  useEffect(() => { setPicked((p) => (p.length ? p.filter((id) => accounts.some((a) => a.id === id)) : accounts.filter((a) => a.active).map((a) => a.id))) }, [accounts])

  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])

  async function analyze(f = file) {
    setAi({ state: "working", reason: "" })
    try {
      const d = await analyzeVideo(f, lang, hint)
      setCopy(fromAi(d.copy)); setFound({ meta: d.meta, description: d.description }); setAi({ state: "done", reason: "" })
    } catch (e) { setAi({ state: "error", reason: e.message }) }
  }

  function chooseFile(f) {
    setFile(f); setFound(null); setCopy(emptyCopy()); setAi((a) => ({ ...a, state: a.state === "off" ? "off" : "idle" }))
    if (f && ai.state !== "off") analyze(f)
  }

  const yt = accounts.some((a) => a.platform === "youtube" && picked.includes(a.id))
  const ig = accounts.some((a) => a.platform === "instagram" && picked.includes(a.id))
  const problem = !file ? "Choose a video first." : !picked.length ? "Choose at least one account."
    : yt && !copy.youtube.title.trim() ? "YouTube needs a title."
    : yt && copy.youtube.title.length > LIMITS.ytTitle ? "YouTube title is too long."
    : ig && (copy.instagram.caption + copy.instagram.hashtags).length > LIMITS.igCaption ? "Instagram caption is too long."
    : mode === "schedule" && !when ? "Pick a date and time." : ""
  const ready = !problem && ai.state !== "working"

  const names = accounts.filter((a) => picked.includes(a.id)).map((a) => `${a.platform} @${a.username}`).join(", ")
  const summary = file && picked.length ? `${mode === "now" ? "Will publish immediately" : "Will be scheduled"} to ${names}.` : ""

  async function publish() {
    setBusy(true); setMsg(null)
    const f = new FormData()
    f.append("file", file); f.append("texts", JSON.stringify(toPayload(copy))); f.append("mode", mode); f.append("tz", TZ)
    picked.forEach((id) => f.append("account_ids", id))
    if (mode === "schedule") f.append("scheduled_at", when.slice(0, 16))
    try {
      const d = await createPost(f)
      const bad = d.items.some((i) => i.status === "FAILED")
      setMsg(bad ? { status: "error", title: "Not published", description: d.items.map((i) => i.error).filter(Boolean).join("; ") || "See the history below." }
        : { status: "success", title: mode === "now" ? "Published" : "Scheduled", description: "Track it in the history below." })
      setFile(null); setFound(null); setCopy(emptyCopy()); setWhen(undefined); setAi((a) => ({ ...a, state: a.state === "off" ? "off" : "idle" }))
      onDone()
    } catch (e) { setMsg({ status: "error", title: "Could not publish", description: e.message }) }
    finally { setBusy(false) }
  }

  return (
    <div className="stack">
      {msg && <Banner status={msg.status} title={msg.title} description={msg.description} isDismissable onDismiss={() => setMsg(null)} />}
      <div className="grid">
        <Step n="1" title="Upload the video">
          <UploadStep file={file} preview={preview} onFile={chooseFile} lang={lang} setLang={setLang} hint={hint} setHint={setHint}
            ai={ai} found={found} onAnalyze={() => analyze()} />
        </Step>
        <Step n="2" title="Check the text" dim={!file}>
          <CopyEditor accounts={accounts} picked={picked} setPicked={setPicked} copy={copy} setCopy={setCopy} aiDone={ai.state === "done"} />
        </Step>
        <div className="rail">
          <Step n="3" title="Choose the time" dim={!file}>
            <WhenStep mode={mode} setMode={setMode} when={when} setWhen={setWhen} busy={busy} ready={ready} onPublish={publish} why={problem} summary={summary} />
          </Step>
          {file && accounts.filter((a) => picked.includes(a.id) && copy[a.platform]).map((a) => (
            <PostPreview key={a.id} platform={a.platform} handle={a.username} copy={copy[a.platform]} src={preview} />
          ))}
        </div>
      </div>
    </div>
  )
}
