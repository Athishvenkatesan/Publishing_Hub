// One metric over time: a 2 px line, a faint area wash, hairline grid, a snapping crosshair with a tooltip, and a table view.
import { useMemo, useRef, useState } from "react"
import { compact, shortDate } from "../../lib/format.js"

const W = 760, H = 250, PAD = { l: 46, r: 18, t: 14, b: 28 }

function niceTicks(max) {
  if (max <= 0) return [0, 1]
  const raw = max / 4, mag = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw)
  return Array.from({ length: Math.ceil(max / step) + 1 }, (_, i) => i * step)
}

export default function LineChart({ data, name, format = compact }) {
  const [hover, setHover] = useState(null)
  const [table, setTable] = useState(false)
  const box = useRef(null)
  const g = useMemo(() => {
    const ticks = niceTicks(Math.max(...data.map((d) => d.y), 0)), top = ticks[ticks.length - 1] || 1
    const x = (i) => PAD.l + (data.length < 2 ? 0 : (i / (data.length - 1)) * (W - PAD.l - PAD.r))
    const y = (v) => H - PAD.b - (v / top) * (H - PAD.t - PAD.b)
    const line = data.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d.y).toFixed(1)}`).join(" ")
    return { ticks, x, y, line, area: data.length ? `${line} L${x(data.length - 1)},${H - PAD.b} L${x(0)},${H - PAD.b} Z` : "" }
  }, [data])
  if (!data.length) return <p className="muted">No data for this period.</p>

  const at = (clientX) => {
    const r = box.current.getBoundingClientRect(), px = ((clientX - r.left) / r.width) * W
    return Math.min(data.length - 1, Math.max(0, Math.round(((px - PAD.l) / (W - PAD.l - PAD.r)) * (data.length - 1))))
  }
  const key = (e) => {
    if (e.key === "ArrowLeft") setHover((h) => Math.max(0, (h ?? data.length) - 1))
    if (e.key === "ArrowRight") setHover((h) => Math.min(data.length - 1, (h ?? -1) + 1))
    if (e.key === "Escape") setHover(null)
  }
  const last = data.length - 1, h = hover
  return (
    <div className="linechart">
      <div className="chart-bar"><button type="button" className="linkbtn no-print" onClick={() => setTable(!table)}>{table ? "Chart view" : "Table view"}</button></div>
      {table ? (
        <div className="table-wrap"><table className="mini"><thead><tr><th>Date</th><th>{name}</th></tr></thead>
          <tbody>{data.map((d) => <tr key={d.x}><td>{d.x}</td><td>{format(d.y)}</td></tr>)}</tbody></table></div>
      ) : (
        <div className="chart-box" ref={box}>
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${name} per day`} tabIndex={0} onKeyDown={key} onBlur={() => setHover(null)}
            onPointerMove={(e) => setHover(at(e.clientX))} onPointerLeave={() => setHover(null)}>
            {g.ticks.map((t) => (
              <g key={t}><line x1={PAD.l} x2={W - PAD.r} y1={g.y(t)} y2={g.y(t)} className="grid" />
                <text x={PAD.l - 8} y={g.y(t) + 4} textAnchor="end" className="axis">{compact(t)}</text></g>
            ))}
            {[0, Math.floor(last / 2), last].filter((v, i, a) => a.indexOf(v) === i).map((i) => (
              <text key={i} x={g.x(i)} y={H - 8} textAnchor={i === 0 ? "start" : i === last ? "end" : "middle"} className="axis">{shortDate(data[i].x)}</text>
            ))}
            <path d={g.area} fill="var(--color-accent)" opacity="0.1" />
            <path d={g.line} fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
            {h != null && <line x1={g.x(h)} x2={g.x(h)} y1={PAD.t} y2={H - PAD.b} className="cross" />}
            <circle cx={g.x(h ?? last)} cy={g.y(data[h ?? last].y)} r="4.5" fill="var(--color-accent)" stroke="var(--color-background-surface, #fff)" strokeWidth="2" />
          </svg>
          {h != null && (
            <div className="tip" style={{ left: `${(g.x(h) / W) * 100}%` }} role="status">
              <span className="tip-value">{format(data[h].y)}</span><span className="tip-label">{name}</span><span className="tip-label">{shortDate(data[h].x)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
