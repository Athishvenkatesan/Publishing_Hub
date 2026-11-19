// File picker built on a native <label> + <input type="file">, so the browser opens its own dialog on click.
// (No script-triggered click, which some browsers block or fire twice.) Also accepts drag and drop.
import { useId, useState } from "react"
import { Text } from "@astryxdesign/core/Text"

export default function FilePick({ label, description, accept, maxMB, value, onChange }) {
  const id = useId()
  const [err, setErr] = useState("")
  const [drag, setDrag] = useState(false)
  const allowed = accept.split(",").map((a) => a.trim())

  function take(f) {
    if (!f) return
    if (f.type && !allowed.includes(f.type)) return setErr(`That file type is not allowed (${f.type}).`)
    if (f.size > maxMB * 1024 * 1024) return setErr(`That file is over ${maxMB} MB.`)
    setErr(""); onChange(f)
  }

  return (
    <div className="fp">
      <span className="fp-label">{label}</span>
      {description && <Text size="sm" color="secondary">{description}</Text>}
      <label htmlFor={id} className={`fp-box${drag ? " fp-box--drag" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); take(e.dataTransfer.files?.[0]) }}>
        <input id={id} type="file" accept={accept} className="fp-input"
          onChange={(e) => { take(e.target.files?.[0]); e.target.value = "" }} />
        <span className="fp-btn">{value ? "Change file" : "Choose file"}</span>
        <span className="fp-name">{value ? value.name : "or drop it here"}</span>
      </label>
      {value && <button type="button" className="fp-clear" onClick={() => { setErr(""); onChange(null) }}>Remove file</button>}
      {err && <Text size="sm" color="error">{err}</Text>}
    </div>
  )
}
