// Slide-in panel to edit an account on any manager screen. It opens filled with the saved values (secrets and tokens included,
// hidden behind Show), so you see what is there now and change only what you need.
// `fields`: [{ name, label, type: "text" | "secret" | "date", placeholder, help }]. `load()` returns the saved values.
import { useEffect, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Heading } from "@astryxdesign/core/Heading"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { TextInput } from "@astryxdesign/core/TextInput"

// Only what changed is sent (trimmed). A cleared date or token is sent as "" so the backend removes it.
export function changes(fields, start, values) {
  return Object.fromEntries(fields.filter((f) => (values[f.name] ?? "").trim() !== (start[f.name] ?? "").trim())
    .map((f) => [f.name, (values[f.name] ?? "").trim()]))
}

function Secret({ f, value, onChange }) {
  const [show, setShow] = useState(false)
  return (
    <label className="sel-wrap"><span className="fp-label">{f.label}</span>
      <span className="secret-row">
        <input className="sel" type={show ? "text" : "password"} autoComplete="off" spellCheck={false} value={value} onChange={(e) => onChange(e.target.value)} placeholder={f.placeholder} />
        <button type="button" className="linkbtn" onClick={() => setShow(!show)}>{show ? "Hide" : "Show"}</button>
      </span>
    </label>
  )
}

export default function MgrEditPanel({ open, title, sub, fields, load, onSave, onClose }) {
  const [start, setStart] = useState(null)
  const [values, setValues] = useState({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")
  useEffect(() => {
    if (!open) return
    setStart(null); setErr("")
    load().then((v) => { setStart(v); setValues(v) }).catch((e) => setErr(e.message))
  }, [open])  // eslint-disable-line react-hooks/exhaustive-deps
  const set = (k) => (v) => setValues((cur) => ({ ...cur, [k]: v }))
  const diff = start ? changes(fields, start, values) : {}

  async function save() {
    setBusy(true); setErr("")
    try { await onSave(diff) } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <>
      <div className={`scrim${open ? " scrim--on" : ""}`} onClick={onClose} />
      <aside className={`drawer${open ? " drawer--on" : ""}`} aria-hidden={!open}>
        <header className="drawer-head">
          <div><Heading level={3}>{title}</Heading>{sub && <Text size="sm" color="secondary">{sub}</Text>}</div>
          <Button variant="secondary" size="sm" label="Close" onClick={onClose} />
        </header>
        {err && <Banner status="error" title="Could not complete" description={err} />}
        {open && !start && !err && <div className="working"><Spinner /><Text size="sm">Loading the saved values...</Text></div>}
        {open && start && fields.map((f) => (
          <div key={f.name} className="stack stack--tight">
            {f.type === "text" ? <TextInput label={f.label} value={values[f.name] ?? ""} onChange={set(f.name)} placeholder={f.placeholder} />
              : f.type === "secret" ? <Secret f={f} value={values[f.name] ?? ""} onChange={set(f.name)} />
              : <label className="sel-wrap"><span className="fp-label">{f.label}</span>
                <input className="sel" type="date" value={values[f.name] ?? ""} onChange={(e) => set(f.name)(e.target.value)} /></label>}
            {f.help && <Text size="sm" color="secondary">{f.help}</Text>}
          </div>
        ))}
        {start && (
          <>
            <div className="row-btns">
              <Button label="Save changes" isLoading={busy} isDisabled={busy || !Object.keys(diff).length} onClick={save} />
              <Button variant="secondary" label="Cancel" onClick={onClose} />
            </div>
            <Text size="sm" color="secondary">{Object.keys(diff).length ? `Will save: ${Object.keys(diff).map((k) => fields.find((f) => f.name === k)?.label).join(", ")}.` : "These are the saved values. Change any of them to save."}</Text>
          </>
        )}
      </aside>
    </>
  )
}
