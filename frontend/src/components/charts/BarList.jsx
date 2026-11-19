// Ranked horizontal bars: one hue, one baseline, the value at the tip. For "which is biggest" questions.
import { compact } from "../../lib/format.js"

export default function BarList({ rows, format = compact, empty = "No data for this period." }) {
  if (!rows.length) return <p className="muted">{empty}</p>
  const max = Math.max(...rows.map((r) => r.value), 1)
  return (
    <ul className="bars">
      {rows.map((r) => (
        <li key={r.key || r.label} title={`${r.label}: ${format(r.value)}${r.note ? " - " + r.note : ""}`}>
          <span className="bars-label">{r.label}</span>
          <span className="bars-track"><span className="bars-fill" style={{ width: `${Math.max(2, (r.value / max) * 100)}%` }} /></span>
          <span className="bars-value">{format(r.value)}</span>
        </li>
      ))}
    </ul>
  )
}
