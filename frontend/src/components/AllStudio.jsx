// The combined screen's working area: one video, one AI run, a review tab per platform, then post to the platforms you switch on.
import { useEffect, useMemo, useRef, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"
import { analyzeStatus } from "../lib/api.js"
import { PLATFORMS, aiKey, allAnalyze, draftsToForms, freshForms } from "../lib/all.js"
import { publishAll, retryOnly, summarise } from "../lib/allPublish.js"
import { autoPlan } from "../lib/allAuto.js"
import { metaAuto } from "../lib/metaAll.js"
import { ytSuggestChannels } from "../lib/api.js"
import { soleAccount } from "../lib/li.js"
import AllPicker from "./AllPicker.jsx"
import LiUpload from "./LiUpload.jsx"
import Step from "./Step.jsx"

export default function AllStudio({ data, onDone }) {
  const [file, setFile] = useState(null)
  const [lang, setLang] = useState("en")
  const [hint, setHint] = useState("")
  const [ai, setAi] = useState({ state: "idle", reason: "" })
  const [found, setFound] = useState(null)
  const [forms, setForms] = useState(freshForms)
  const [off, setOff] = useState([])            // platforms the user switched off (or that already went live in this round)
  const [targets, setTargets] = useState({})    // platform kind -> account keys
  const [tab, setTab] = useState("")
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const [why, setWhy] = useState({})          // platform kind -> why the AI ticked or switched it
  const byHand = useRef({ platforms: {}, accounts: {} })  // what the user changed by hand: the AI never overrides it
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])
  useEffect(() => { analyzeStatus().then((s) => !s.ready && setAi({ state: "off", reason: `${s.reason} The posts still work: write them yourself.` })).catch(() => {}) }, [])

  const by = Object.fromEntries(data.map((d) => [d.p.kind, d]))
  const soles = JSON.stringify(Object.fromEntries(PLATFORMS.map((p) => [p.kind, soleAccount(by[p.kind].accounts)])))
  useEffect(() => {  // a platform with a single signed-in account has that account ticked for you
    const s = JSON.parse(soles)
    setTargets((cur) => ({ ...cur, ...Object.fromEntries(PLATFORMS.filter((p) => s[p.kind] && !byHand.current.accounts[p.kind]).map((p) => [p.kind, [s[p.kind]]])) }))
  }, [soles])

  const on = PLATFORMS.filter((p) => !p.soon && by[p.kind].accounts.some((a) => a.connected) && !off.includes(p.kind))
  const picked = (p) => (targets[p.kind] || []).filter((k) => by[p.kind].accounts.some((a) => a.key === k && a.connected))
  const active = on.find((p) => p.kind === tab) || on[0]

  async function analyze(v = file) {
    setAi({ state: "working", reason: "" })
    try {
      const d = await allAnalyze(v, lang, hint)
      setForms((cur) => draftsToForms(d, cur)); setFound({ meta: d.meta, description: d.description, drafts: d }); setAi({ state: "done", reason: "" })
      autoPick(d)
    } catch (e) { setAi({ state: "error", reason: e.message }) }
  }
  // After the AI has watched the video: tick the platforms and channels that fit it (never over the person's own choices).
  async function autoPick(d) {
    const kids = d.youtube?.suggestions?.made_for_kids?.value ?? false
    let channels = null
    try { channels = await ytSuggestChannels({ description: d.description, title: d.youtube?.title || "", kids }) } catch { /* no suggestion: the channels stay as they are */ }
    const plan = autoPlan({ kids, channels, youtubeAccounts: by.youtube.accounts, metaTargets: metaAuto(by.meta.accounts), hand: byHand.current })
    setOff((cur) => [...new Set([...cur, ...plan.off])]); setTargets((cur) => ({ ...cur, ...plan.targets })); setWhy(plan.why)
  }
  function chooseFile(v) {
    byHand.current = { platforms: {}, accounts: {} }; setOff([]); setWhy({}); setTargets(JSON.parse(soles) ? Object.fromEntries(Object.entries(JSON.parse(soles)).filter(([, k]) => k).map(([p, k]) => [p, [k]])) : {})
    setFile(v); setFound(null); setForms(freshForms()); setMsg(null); setAi((a) => ({ ...a, state: a.state === "off" ? "off" : "idle" }))
    if (v && ai.state !== "off") analyze(v)
  }

  const problem = !file ? "Choose a video first." : !on.length ? "Switch on at least one platform." : ai.state === "working" ? "The AI is still analysing."
    : on.map((p) => (!picked(p).length ? `Choose a ${p.name} account.` : p.problem(forms[p.kind], picked(p)))).find(Boolean) || ""

  async function publish() {
    setBusy(true); setMsg(null)
    try {
      const results = await publishAll(file, on.map((p) => ({ kind: p.kind, name: p.name, publish: p.api.publish, toForm: p.toForm, form: forms[p.kind], accounts: picked(p) })))
      setMsg(summarise(results))
      const done = retryOnly(results)
      if (done.length === results.length) { setFile(null); setFound(null); setForms(freshForms()); setOff([]); setAi((a) => ({ ...a, state: a.state === "off" ? "off" : "idle" })) }
      else setOff((cur) => [...cur, ...done])  // press Post again to retry only the ones that failed
      onDone()
    } finally { setBusy(false) }
  }

  return (
    <div className="stack">
      {msg && <Banner status={msg.status} title={msg.title} description={msg.description} isDismissable onDismiss={() => setMsg(null)} />}
      <div className="grid">
        <div className="stack">
          <Step n="2" title="Upload the video" dim={!on.length && !file}>
            <LiUpload file={file} preview={preview} onFile={chooseFile} lang={lang} setLang={setLang} hint={hint} setHint={setHint} ai={ai} found={found} onAnalyze={() => analyze()}
              accept="video/mp4" description="MP4, up to 300 MB (LinkedIn takes MP4 only)." working="the YouTube, LinkedIn, X and Meta posts" note="writes all four posts" />
          </Step>
        </div>
        <Step n="3" title="Check each post">
          {active ? (
            <div className="stack">
              <SegmentedControl label="Platform" value={active.kind} onChange={setTab}>
                {on.map((p) => <SegmentedControlItem key={p.kind} value={p.kind} label={p.name} />)}
              </SegmentedControl>
              <active.Review key={active.kind} f={forms[active.kind]} setF={(f) => setForms({ ...forms, [active.kind]: f })}
                {...(active.kind === "youtube" ? { yt: found?.drafts.youtube } : { draft: found?.drafts[aiKey(active)] })} aiDone={ai.state === "done"} />
            </div>
          ) : <Text color="secondary">Switch on a platform to write its post.</Text>}
        </Step>
        <div className="rail">
          <Step n="4" title="Choose where to post">
            <div className="stack">
              {PLATFORMS.map((p) => (
                <AllPicker key={p.kind} p={p} accounts={by[p.kind].accounts} profiles={by[p.kind].profiles} enabled={on.includes(p)}
                  why={why[p.kind]} onToggle={(v) => { byHand.current.platforms[p.kind] = true; setOff((cur) => (v ? cur.filter((k) => k !== p.kind) : [...cur, p.kind])) }}
                  value={targets[p.kind] || []} onChange={(t) => { byHand.current.accounts[p.kind] = true; setTargets({ ...targets, [p.kind]: t }) }} />
              ))}
              <Button size="lg" label={`Post to ${on.length} ${on.length === 1 ? "platform" : "platforms"}`} isLoading={busy} isDisabled={!!problem || busy} onClick={publish} />
              {problem ? <Text size="sm" color="secondary">{problem}</Text> : <Text size="sm" weight="semibold">Posts now, one platform after another. If one fails, the others still go out.</Text>}
              {busy && <Text size="sm" color="secondary">Uploading. A large video goes up once per platform and can take a few minutes.</Text>}
            </div>
          </Step>
        </div>
      </div>
    </div>
  )
}
