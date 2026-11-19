// A headline number with its change against the previous period and a small trend line. Click to chart it.
import { Text } from "@astryxdesign/core/Text"
import { change } from "../../lib/format.js"

function Spark({ values }) {
  if (!values || values.length < 2) return null
  const w = 96, h = 28, max = Math.max(...values, 1), min = Math.min(...values, 0)
  const pts = values.map((v, i) => [(i / (values.length - 1)) * (w - 8) + 4, h - 4 - ((v - min) / ((max - min) || 1)) * (h - 8)])
  const [lx, ly] = pts[pts.length - 1]
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <polyline points={pts.map((p) => p.join(",")).join(" ")} fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="4" fill="var(--color-accent)" stroke="var(--color-background-surface, #fff)" strokeWidth="2" />
    </svg>
  )
}

export default function StatTile({ label, value, cur, prev, spark, active, onClick, hint }) {
  const d = prev === undefined ? null : change(cur, prev)
  const Tag = onClick ? "button" : "div"
  return (
    <Tag type={onClick ? "button" : undefined} className={`tile${active ? " tile--on" : ""}${onClick ? " tile--btn" : ""}`} onClick={onClick} aria-pressed={onClick ? !!active : undefined}>
      <Text size="sm" color="secondary">{label}</Text>
      <span className="tile-value">{value}</span>
      <span className="tile-foot">
        {d && <Text size="sm" color="secondary">{d.dir > 0 ? "▲" : d.dir < 0 ? "▼" : "–"} {d.text} vs previous</Text>}
        {!d && hint && <Text size="sm" color="secondary">{hint}</Text>}
        <Spark values={spark} />
      </span>
    </Tag>
  )
}
