// The Meta screen's working area, same flow as LinkedIn and YouTube: token and Pages, upload + AI analysis,
// check the post, the AI ticks where it goes, then one button publishes.
import { useEffect, useMemo, useRef, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Heading } from "@astryxdesign/core/Heading"
import { analyzeStatus, fbAnalyze, fbPublishMulti } from "../lib/api.js"
import { applyAi, autoTargets, defaults, igAccounts, isIg, postable, problem as findProblem, THREADS, toForm } from "../lib/meta.js"
import { TZ } from "../lib/time.js"
import LiPreviewCard from "./LiPreviewCard.jsx"
import LiUpload from "./LiUpload.jsx"
import MetaOverview from "./MetaOverview.jsx"
import MetaPublish from "./MetaPublish.jsx"
import MetaReview from "./MetaReview.jsx"

const Step = ({ n, title, children, dim }) => (
  <section className={`step${dim ? " step--dim" : ""}`}>
    <div className="step-head"><span className="step-n">{n}</span><Heading level={3}>{title}</Heading></div>
    {children}
  </section>
)

export default function MetaStudio({ check, onCheck, onDone }) {
  const pages = check.data?.pages || []
  const [file, setFile] = useState(null)
  const [lang, setLang] = useState("en")
  const [hint, setHint] = useState("")
  const [f, setF] = useState(defaults())
  const [ai, setAi] = useState({ state: "idle", reason: "" })
  const [found, setFound] = useState(null)
  const [targets, setTargets] = useState([])
  const byHand = useRef(false)   // the user changed the ticks themselves: never tick again behind their back
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])
  useEffect(() => { analyzeStatus().then((s) => !s.ready && setAi({ state: "off", reason: `${s.reason} You can still write the post yourself.` })).catch(() => {}) }, [])
  const caps = check.data?.capabilities || []
  const ok = (k) => !!caps.find((c) => c.key === k)?.ok
  const fbReady = ok("facebook_video"), igReady = ok("instagram_video"), thReady = ok("threads_video")
  useEffect(() => { if (file) setTargets((cur) => autoTargets({ pages, fbReady, igReady, thReady, aiState: ai.state, byHand: byHand.current, current: cur })) }, [file, pages, fbReady, igReady, thReady, ai.state])

  const allowed = [...(fbReady ? postable(pages).map((p) => p.id) : []), ...(igReady ? igAccounts(pages).map((a) => a.key) : []), ...(thReady ? [THREADS] : [])]
  const picked = targets.filter((k) => allowed.includes(k))
  const names = postable(pages).filter((p) => picked.includes(p.id)).map((p) => p.name.trim())
  const problem = !file ? "Choose a video first." : ai.state === "working" ? "The AI is still analysing." : findProblem(f, picked)

  async function analyze(v = file) {
    setAi({ state: "working", reason: "" })
    try {
      const d = await fbAnalyze(v, lang, hint)
      setF((cur) => applyAi(cur, d.facebook)); setFound({ meta: d.meta, description: d.description, draft: d.facebook }); setAi({ state: "done", reason: "" })
    } catch (e) { setAi({ state: "error", reason: e.message }) }
  }
  function reset() {
    setFile(null); setFound(null); setF(defaults()); setTargets([]); byHand.current = false
    setAi((a) => ({ ...a, state: a.state === "off" ? "off" : "idle" }))
  }
  function chooseFile(v) {
    reset(); setFile(v)
    if (v && ai.state !== "off") analyze(v)
  }

  async function publish() {
    setBusy(true); setMsg(null)
    try {
      const d = await fbPublishMulti(toForm(file, f, picked, TZ))
      const done = d.items.length, bad = d.errors || []
      const failed = bad.map((e) => `${pages.find((p) => p.id === e.key)?.name.trim() || e.label}: ${e.error}`).join(" | ")
      if (!done) { setMsg({ status: "error", title: "Could not post", description: failed }); return }  // keep the form so it can be retried
      const where = d.items.map((i) => (i.platform === "facebook" ? `Facebook ${i.account_name.trim()}` : i.platform === "threads" ? `Threads @${i.account_name}` : `Instagram @${i.account_name}`)).join(" and ")
      const verb = f.mode === "now" ? "Sent" : "Scheduled"
      setMsg({ status: bad.length ? "warning" : "success", title: bad.length ? `${verb} to ${done} of ${done + bad.length}` : `${verb} to ${where}`,
        description: bad.length ? `Failed: ${failed}. Done: ${where}.` : "Facebook processes the video for a minute or two. Track it in the history below." })
      reset(); onDone()
    } catch (e) { setMsg({ status: "error", title: "Could not post", description: e.message }) } finally { setBusy(false) }
  }

  return (
    <div className="stack">
      {msg && <Banner status={msg.status} title={msg.title} description={msg.description} isDismissable onDismiss={() => setMsg(null)} />}
      <div className="grid">
        <div className="stack">
          <Step n="1" title="Your token and Pages"><MetaOverview state={check} onCheck={onCheck} /></Step>
          <Step n="2" title="Upload the video" dim={!postable(pages).length}>
            <LiUpload accept="video/mp4,video/quicktime" description="MP4 or MOV, up to 300 MB." working="the Facebook post" note="posts as a Facebook Page video"
              file={file} preview={preview} onFile={chooseFile} lang={lang} setLang={setLang} hint={hint} setHint={setHint} ai={ai} found={found} onAnalyze={() => analyze()} />
          </Step>
        </div>
        <Step n="3" title="Check the post" dim={!file}><MetaReview f={f} setF={setF} draft={found?.draft} aiDone={ai.state === "done"} showCaption={picked.some(isIg) || picked.includes(THREADS)} /></Step>
        <div className="rail">
          <Step n="4" title="Choose where to post" dim={!file}>
            <MetaPublish f={f} setF={setF} pages={pages} caps={caps} value={picked} auto={!byHand.current && picked.length > 0}
              onChange={(t) => { byHand.current = true; setTargets(t) }} busy={busy} problem={problem} onPublish={publish} />
          </Step>
          {file && <LiPreviewCard video={preview} text={[f.title, f.text].filter(Boolean).join("\n")} name={names[0] || "Your Page"} visibility="PUBLIC" />}
        </div>
      </div>
    </div>
  )
}
