// The LinkedIn and X screens' working area: accounts, upload + AI analysis, review the post, choose where it goes and post it.
// Everything platform-specific comes from `p` (lib/platforms.js).
import { useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router"
import { Banner } from "@astryxdesign/core/Banner"
import { Heading } from "@astryxdesign/core/Heading"
import { analyzeStatus } from "../lib/api.js"
import { soleAccount } from "../lib/li.js"
import { popupFailure } from "../lib/liPopup.js"
import LiUpload from "./LiUpload.jsx"
import MgrAddPanel from "./MgrAddPanel.jsx"
import YtChannelPicker from "./YtChannelPicker.jsx"
import YtOverview from "./YtOverview.jsx"

const Step = ({ n, title, children, dim }) => (
  <section className={`step${dim ? " step--dim" : ""}`}>
    <div className="step-head"><span className="step-n">{n}</span><Heading level={3}>{title}</Heading></div>
    {children}
  </section>
)

export default function PostStudio({ p, accounts, profiles, redirectUri, notice, loading, reload, onDone }) {
  const { defaults, applyAi, toForm, Review, Publish, Preview } = p
  const [file, setFile] = useState(null)
  const [lang, setLang] = useState("en")
  const [hint, setHint] = useState("")
  const [f, setF] = useState(defaults())
  const [ai, setAi] = useState({ state: "idle", reason: "" })
  const [found, setFound] = useState(null)
  const [targets, setTargets] = useState([])   // one signed-in account is ticked for you; with several, pick who it posts as
  const byHand = useRef(false)                 // the user changed the ticks themselves: never tick again behind their back
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const [adding, setAdding] = useState(false)
  const navigate = useNavigate()
  const connected = accounts.some((a) => a.connected)
  const picked = targets.filter((k) => accounts.some((a) => a.key === k && a.connected))
  const names = picked.map((k) => profiles[k]?.title || accounts.find((a) => a.key === k)?.label || k)
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  const sole = soleAccount(accounts)
  useEffect(() => { if (sole && !byHand.current) setTargets([sole]) }, [sole])
  const pickByHand = (t) => { byHand.current = true; setTargets(t) }
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])
  useEffect(() => { analyzeStatus().then((s) => !s.ready && setAi({ state: "off", reason: `${s.reason} The post text still works: write it yourself.` })).catch(() => {}) }, [])

  async function analyze(v = file) {
    setAi({ state: "working", reason: "" })
    try {
      const d = await p.api.analyze(v, lang, hint)
      setF((cur) => applyAi(cur, d[p.aiKey])); setFound({ meta: d.meta, description: d.description, draft: d[p.aiKey] }); setAi({ state: "done", reason: "" })
    } catch (e) { setAi({ state: "error", reason: e.message }) }
  }
  function chooseFile(v) {
    setFile(v); setFound(null); setF(defaults()); setAi((a) => ({ ...a, state: a.state === "off" ? "off" : "idle" }))
    if (v && ai.state !== "off") analyze(v)
  }

  const problem = !picked.length ? (connected ? "Choose at least one signed-in account." : `Connect a ${p.name} account first.`) : !file ? "Choose a video first."
    : p.problem(f) || (ai.state === "working" ? "The AI is still analysing." : "")

  async function publish() {
    setBusy(true); setMsg(null)
    try {
      const d = await p.api.publish(toForm(file, f, picked))
      const ok = d.items.length, bad = d.errors || []
      const failed = bad.map((e) => `${e.label}: ${e.error}`).join(" | ")
      if (!ok) { setMsg({ status: "error", title: `Could not post to ${bad.length === 1 ? "that account" : "any account"}`, description: failed }); return }  // keep the form so it can be retried
      const where = d.items.map((i) => i.account_name).join(" and ")
      setMsg({ status: bad.length ? "warning" : "success", title: bad.length ? `Posted to ${ok} of ${ok + bad.length} accounts` : `Posted to ${where}`,
        description: bad.length ? `Failed: ${failed}. Done: ${where}.` : `It is live on ${p.name}. Open it from the history below.` })
      setFile(null); setFound(null); setF(defaults()); setTargets(sole && !byHand.current ? [sole] : []); setAi((a) => ({ ...a, state: a.state === "off" ? "off" : "idle" })); onDone()
    } catch (e) { setMsg({ status: "error", title: "Could not post", description: e.message }) } finally { setBusy(false) }
  }
  async function connectFromList(key) {
    let reason
    try {
      const r = await p.popup(key)
      if (r.ok) { reload(); setMsg({ status: "success", title: `${p.name} connected`, description: "Tick it in the Post to list." }); return }
      reason = popupFailure(r)
    } catch (e) { reason = e.message }
    navigate(`${p.accountsRoute}?account=${key}&error=${encodeURIComponent(reason)}`)  // the Accounts screen shows the reason beside the buttons that fix it
  }

  return (
    <div className="stack">
      {msg && <Banner status={msg.status} title={msg.title} description={msg.description} isDismissable onDismiss={() => setMsg(null)} />}
      <div className="grid">
        <div className="stack">
          <Step n="1" title="Your accounts"><YtOverview accounts={accounts} profiles={profiles} notice={notice} loading={loading} account="" manageTo={p.accountsRoute} unit={p.unit} studio={false} /></Step>
          <Step n="2" title="Upload the video" dim={!connected}>
            <LiUpload {...p.upload} file={file} preview={preview} onFile={chooseFile} lang={lang} setLang={setLang} hint={hint} setHint={setHint} ai={ai} found={found} onAnalyze={() => analyze()} />
          </Step>
        </div>
        <Step n="3" title="Check the post" dim={!file}><Review f={f} setF={setF} draft={found?.draft} aiDone={ai.state === "done"} /></Step>
        <div className="rail">
          <Step n="4" title="Choose where to post" dim={!file}>
            <Publish f={f} setF={setF} busy={busy} problem={problem} onPublish={publish} count={picked.length} summary={file ? `Will post to ${names.join(" and ")} now.` : ""}
              picker={<YtChannelPicker accounts={accounts} profiles={profiles} value={targets} onChange={pickByHand} noun="account" manageTo={p.accountsRoute}
                onAdd={() => setAdding(true)} onConnect={connectFromList} />} />
          </Step>
          {file && <Preview video={preview} text={f.text} name={names[0]} visibility={f.visibility} />}
        </div>
      </div>
      <MgrAddPanel kind={p.kind} open={adding} preset="" accounts={accounts} redirectUri={redirectUri} onClose={() => setAdding(false)}
        onAdded={() => { setAdding(false); reload(); setMsg({ status: "success", title: "Account added", description: "Open the Post to list and press Connect next to it to sign in." }) }} />
    </div>
  )
}
