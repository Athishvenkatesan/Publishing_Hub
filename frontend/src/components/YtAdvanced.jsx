// YouTube's advanced upload options, collapsed by default like on YouTube itself.
import { Text } from "@astryxdesign/core/Text"
import { useEffect, useState } from "react"
import FilePick from "./FilePick.jsx"

const LANGS = [["", "Not set"], ["en", "English"], ["ar", "Arabic"], ["hi", "Hindi"], ["ur", "Urdu"], ["fr", "French"]]

const Sel = ({ label, value, onChange, children }) => (
  <label className="sel-wrap"><span className="fp-label">{label}</span>
    <select className="sel" value={value} onChange={(e) => onChange(e.target.value)}>{children}</select></label>
)
const Chk = ({ label, hint, checked, onChange }) => (
  <label className="chk"><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    <span><b>{label}</b>{hint && <><br /><Text size="sm" color="secondary">{hint}</Text></>}</span></label>
)

export default function YtAdvanced({ f, setF, categories, thumb, setThumb, notes }) {
  const set = (k) => (v) => setF({ ...f, [k]: v })
  const [open, setOpen] = useState(false)
  const ticked = !!(notes?.made_for_kids?.value || notes?.ai_generated?.value)
  useEffect(() => { if (ticked) setOpen(true) }, [ticked])  // show the options the AI just ticked
  return (
    <details className="adv" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>Advanced options{ticked ? " (AI ticked some)" : ""}</summary>
      <div className="stack adv-body">
        <Sel label="Category" value={f.categoryId} onChange={set("categoryId")}>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Sel>
        <Sel label="Video language" value={f.language} onChange={set("language")}>
          {LANGS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </Sel>
        <Sel label="License" value={f.license} onChange={set("license")}>
          <option value="youtube">Standard YouTube License</option>
          <option value="creativeCommon">Creative Commons - Attribution</option>
        </Sel>
        <Chk label="Made for kids" hint={notes?.made_for_kids ? `AI suggestion: ${notes.made_for_kids.reason}` : "Required by YouTube. Tick only if the video is aimed at children."} checked={f.madeForKids} onChange={set("madeForKids")} />
        <Chk label="Contains AI-generated or altered content" hint={notes?.ai_generated ? `AI suggestion: ${notes.ai_generated.reason}` : "Tick if realistic people, places or events were made or changed with AI."} checked={f.synthetic} onChange={set("synthetic")} />
        <Chk label="Allow embedding on other websites" checked={f.embeddable} onChange={set("embeddable")} />
        <Chk label="Show view and like counts" checked={f.publicStats} onChange={set("publicStats")} />
        <Chk label="Notify subscribers" hint="Sends subscribers a notification when the video goes public." checked={f.notify} onChange={set("notify")} />
        <FilePick label="Custom thumbnail" value={thumb} onChange={setThumb} accept="image/jpeg,image/png" maxMB={2}
          description="Optional. JPG or PNG, up to 2 MB. Your channel must be verified by phone with YouTube." />
      </div>
    </details>
  )
}
