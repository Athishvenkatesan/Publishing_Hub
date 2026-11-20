// The YouTube screen's working area: connect, upload + AI analysis, review + advanced options, time + publish.
import { useEffect, useMemo, useRef, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Heading } from "@astryxdesign/core/Heading"
import { analyzeStatus, connectAccount_, ytAnalyze, ytChannelProfiles, ytPublishMulti, ytSuggestChannels } from "../lib/api.js"
import { TZ } from "../lib/time.js"
import { DESC_MAX, TITLE_MAX, applyAi, defaults, toForm } from "../lib/yt.js"
import { useThumbs } from "../lib/useThumbs.js"
import MgrAddPanel from "./MgrAddPanel.jsx"
import YtAdvanced from "./YtAdvanced.jsx"
import YtChannelPicker from "./YtChannelPicker.jsx"
import YtOverview from "./YtOverview.jsx"
import YtPreviewCard from "./YtPreviewCard.jsx"
import YtReview from "./YtReview.jsx"
import YtThumbs from "./YtThumbs.jsx"
import YtUpload from "./YtUpload.jsx"
import YtWhen from "./YtWhen.jsx"

const Step = ({ n, title, children, dim }) => (
  <section className={`step${dim ? " step--dim" : ""}`}>
    <div className="step-head"><span className="step-n">{n}</span><Heading level={3}>{title}</Heading></div>
    {children}
  </section>
)

export default function YtStudio({ status, loading, notice, reload, onDone, accounts = [], account = "" }) {
  const [file, setFile] = useState(null)
  const [thumb, setThumb] = useState(null)
  const [lang, setLang] = useState("en")
  const [hint, setHint] = useState("")
  const [f, setF] = useState(defaults())
  const [ai, setAi] = useState({ state: "idle", reason: "" })
  const [found, setFound] = useState(null)
  const [mode, setMode] = useState("now")
  const [when, setWhen] = useState(undefined)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const connected = accounts.some((a) => a.connected)
  const [targets, setTargets] = useState([])
  const [profiles, setProfiles] = useState({})   // who each signed-in channel is, by account key
  const [notes, setNotes] = useState(null)       // the AI's reasons for "made for kids" and "AI content"
  const [adding, setAdding] = useState(false)
  const [accMsg, setAccMsg] = useState(null)
  const manual = useRef({ targets: false, kids: false, ai: false, off: new Set() })  // what the user changed by hand: the AI never overrides it (off = channels they unticked)
  const signedIn = accounts.filter((a) => a.connected).map((a) => a.key).join(",")
  useEffect(() => {
    if (!signedIn) { setProfiles({}); return }
    ytChannelProfiles().then((d) => setProfiles(Object.fromEntries(d.profiles.map((p) => [p.key, p])))).catch(() => {})
  }, [signedIn])
  const setTargetsUser = (t) => {
    manual.current.targets = true
    targets.filter((k) => !t.includes(k)).forEach((k) => manual.current.off.add(k)); t.forEach((k) => manual.current.off.delete(k))
    setTargets(t)
  }
  const setFUser = (nf) => {
    if (nf.madeForKids !== f.madeForKids) manual.current.kids = true
    if (nf.synthetic !== f.synthetic) manual.current.ai = true
    setF(nf)
  }
  const picked = targets.filter((k) => accounts.some((a) => a.key === k && a.connected))
  const names = picked.map((k) => accounts.find((a) => a.key === k)?.label || k)
  const th = useThumbs(setThumb)
  const unverified = status?.channel?.verified === false  // YouTube blocks custom thumbnails until the channel is phone-verified
  const thumbUrl = useMemo(() => (thumb ? URL.createObjectURL(thumb) : null), [thumb])
  useEffect(() => () => thumbUrl && URL.revokeObjectURL(thumbUrl), [thumbUrl])

  useEffect(() => {
    analyzeStatus().then((s) => !s.ready && setAi({ state: "off", reason: `${s.reason} The fields still work: write them yourself.` })).catch(() => {})
  }, [])
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])

  async function analyze(v = file) {
    setAi({ state: "working", reason: "" })
    try {
      const d = await ytAnalyze(v, lang, hint)
      const sg = d.youtube.suggestions
      setF((cur) => ({ ...applyAi(cur, d.youtube), madeForKids: manual.current.kids ? cur.madeForKids : sg.made_for_kids.value,
        synthetic: manual.current.ai ? cur.synthetic : sg.ai_generated.value }))  // ticked by the AI unless you already chose
      setNotes(sg); setFound({ meta: d.meta, description: d.description, yt: d.youtube }); setAi({ state: "done", reason: "" })
      th.generate(v, lang, hint, d.description, d.youtube.title, !unverified)
      suggestChannels(d.description, d.youtube.title, sg.made_for_kids.value)
    } catch (e) { setAi({ state: "error", reason: e.message }); th.generate(v, lang, hint, "", "", !unverified) }
  }

  async function suggestChannels(description, title, kids) {
    try {
      const r = await ytSuggestChannels({ description, title, kids })
      const ok = r.recommended.filter((k) => accounts.some((a) => a.key === k && a.connected))
      // The best-fitting channels come ticked. If you already chose some by hand, they stay, and only the ones you did not untick are added.
      if (ok.length) setTargets((cur) => manual.current.targets ? [...new Set([...cur, ...ok.filter((k) => !manual.current.off.has(k))])] : ok)
    } catch { /* no suggestion: the channel stays as chosen */ }
  }

  function chooseFile(v) {
    manual.current = { targets: targets.length > 0, kids: false, ai: false, off: new Set() }; setNotes(null)  // nothing is ticked for you: the AI ticks after it analyses (channels you already ticked stay)
    setFile(v); setFound(null); setF(defaults()); setAi((a) => ({ ...a, state: a.state === "off" ? "off" : "idle" }))
    th.clear()
    if (v && ai.state !== "off") analyze(v)
    else if (v) th.generate(v, lang, hint, "", "", !unverified)
  }

  const problem = !picked.length ? (accounts.some((a) => a.connected) ? "Choose at least one connected account." : "Connect YouTube first.") : !file ? "Choose a video first." : !f.title.trim() ? "YouTube needs a title."
    : f.title.length > TITLE_MAX ? "Title is over 100 characters." : f.description.length > DESC_MAX ? "Description is over 5,000 characters."
    : mode === "schedule" && !when ? "Pick a date and time." : ai.state === "working" ? "The AI is still analysing." : ""
  const summary = file ? (mode === "now" ? `Will upload to ${names.join(" and ") || "your channel"} now as ${f.privacy}.` : `Will be scheduled on ${names.join(" and ") || "your channel"} for`) : ""

  async function publish() {
    setBusy(true); setMsg(null)
    try {
      const d = await ytPublishMulti(toForm(file, f, thumb, mode, when, TZ, picked))
      const ok = d.items.length, bad = d.errors || []
      const warn = (d.warnings || []).join(" ")
      const verb = mode === "now" ? "Uploaded to" : "Scheduled on"
      const where = d.items.map((i) => i.account_name).join(" and ")
      const failed = bad.map((e) => `${e.label}: ${e.error}`).join(" | ")
      const after = d.thumbnail === "pending" ? " The thumbnail is added when YouTube finishes processing." : ""
      if (!ok) { setMsg({ status: "error", title: `Could not upload to ${bad.length === 1 ? "that account" : "any account"}`, description: failed }); return }  // keep the form so it can be retried
      setMsg({ status: bad.length || warn ? "warning" : "success", title: bad.length ? `${verb} ${ok} of ${ok + bad.length} accounts` : `${verb} ${where}`,
        description: [bad.length ? `Failed: ${failed}.` : `YouTube is processing it. Track it in the history below.${after}`, bad.length ? `Done: ${where}.` : "", warn].filter(Boolean).join(" ") })
      th.clear(); setFile(null); setThumb(null); setFound(null); setF(defaults()); setWhen(undefined); setTargets([]); manual.current.targets = false
      setAi((a) => ({ ...a, state: a.state === "off" ? "off" : "idle" })); onDone()
    } catch (e) { setMsg({ status: "error", title: "Could not upload", description: e.message }) }
    finally { setBusy(false) }
  }

  async function connectFromList(key) {
    try { window.location.href = (await connectAccount_(key, {}, "youtube")).url }
    catch (e) { setAccMsg({ status: "error", title: "Could not connect that channel", description: e.message }) }  // Google would refuse: say why here
  }

  return (
    <div className="stack">
      {accMsg && <Banner status={accMsg.status} title={accMsg.title} description={accMsg.description} isDismissable onDismiss={() => setAccMsg(null)} />}
      {msg && <Banner status={msg.status} title={msg.title} description={msg.description} isDismissable onDismiss={() => setMsg(null)} />}
      <div className="grid">
        <div className="stack">
          <Step n="1" title="Your accounts">
            <YtOverview accounts={accounts} profiles={profiles} notice={notice} loading={loading} account={account} />
          </Step>
          <Step n="2" title="Upload the video" dim={!connected}>
            <YtUpload file={file} preview={preview} onFile={chooseFile} lang={lang} setLang={setLang} hint={hint} setHint={setHint}
              ai={ai} found={found} onAnalyze={() => analyze()} />
          </Step>
        </div>
        <Step n="3" title="Check the details" dim={!file}>
          <YtReview f={f} setF={setFUser} yt={found?.yt} aiDone={ai.state === "done"} />
          <YtThumbs th={th} file={file} onRegenerate={() => th.generate(file, lang, hint, found?.description || "", f.title, !unverified)}
            unverified={unverified} verifyUrl={status?.channel?.verify_url} />
          <YtAdvanced f={f} setF={setFUser} notes={notes} categories={status?.categories || []} thumb={thumb} setThumb={(x) => { th.useOwn(); setThumb(x) }} />
        </Step>
        <div className="rail">
          <Step n="4" title="Choose the time" dim={!file}>
            <YtWhen f={f} setF={setF} mode={mode} setMode={setMode} when={when} setWhen={setWhen} busy={busy}
              problem={problem} onPublish={publish} summary={summary} count={picked.length}
              picker={<YtChannelPicker accounts={accounts} profiles={profiles} value={targets} onChange={setTargetsUser} kids={file ? f.madeForKids : null}
                onAdd={() => setAdding(true)} onConnect={connectFromList} />} />
          </Step>
          {file && <YtPreviewCard thumb={thumbUrl} title={f.title} channel={status?.channel?.title} short={found?.yt?.format === "short"} />}
        </div>
      </div>
      <MgrAddPanel open={adding} preset="" accounts={accounts} onClose={() => setAdding(false)}
        onAdded={() => { setAdding(false); reload(); setAccMsg({ status: "success", title: "Channel added", description: "Open the Post to list and press Connect next to it to sign in." }) }} />
    </div>
  )
}
