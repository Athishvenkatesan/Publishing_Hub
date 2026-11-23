import { Badge } from "@astryxdesign/core/Badge"
import { Table, proportional, pixel } from "@astryxdesign/core/Table"
import { Text } from "@astryxdesign/core/Text"
import { fmt } from "../lib/time.js"

const STATUS = {
  PUBLISHED: { variant: "success", label: "Published" },
  SCHEDULED: { variant: "info", label: "Scheduled - not published yet" },
  PUBLISHING: { variant: "warning", label: "Publishing..." },
  FAILED: { variant: "error", label: "Failed - not published" },
  CANCELLED: { variant: "neutral", label: "Cancelled" },
}

// One video posted to several channels at once shares a group_id: show it as one row that lists each channel.
export function groupRows(items) {
  const by = new Map()
  items.forEach((r) => { const g = by.get(r.group_id); if (g) g.rows.push(r); else by.set(r.group_id, { ...r, rows: [r] }) })
  return [...by.values()]
}
const lines = (r) => r.rows || [r]
const name = (x) => (x.platform === "youtube-direct" ? `YouTube - ${x.account_name}` : x.platform === "linkedin" ? `LinkedIn - ${x.account_name}` : `${x.platform} - @${x.account_name}`)

const base = [
  { key: "when", header: "When", width: pixel(150),
    renderCell: (r) => <Text size="sm">{r.mode === "schedule" ? fmt(r.scheduled_for, r.timezone) : fmt(r.created_at)}</Text> },
  { key: "video", header: "Video", width: proportional({ minWidth: 150 }),
    renderCell: (r) => <div><div><Text weight="semibold" size="sm">{r.title || r.filename}</Text></div>
      {r.caption && <div><Text size="sm" color="secondary">{r.caption.slice(0, 70)}</Text></div>}</div> },
  { key: "account", header: "Account", width: pixel(230),
    renderCell: (r) => lines(r).length > 1
      ? <div>{lines(r).map((x) => <div key={x.id} className="chan-line" title={x.account_name}><Text size="sm">{x.account_name}</Text></div>)}</div>
      : <Text size="sm">{name(r)}</Text> },
  { key: "status", header: "Status", width: pixel(230),
    renderCell: (r) => <div>{lines(r).map((x) => { const s = STATUS[x.status] || STATUS.SCHEDULED
      return <div key={x.id} className={lines(r).length > 1 ? "chan-line" : undefined}><Badge variant={s.variant} label={s.label} /></div> })}</div> },
  { key: "link", header: "Post", width: pixel(180),
    renderCell: (r) => r.post_url
      ? <a href={r.post_url} target="_blank" rel="noreferrer">Open post</a>
      : r.error ? <span className="err">{r.error}</span> : <Text size="sm" color="secondary">-</Text> },
]

// With `actions`, the last column becomes "Action" (a menu per row) and any error note moves under the title.
function withActions(actions) {
  return base.slice(0, -1).map((c) => c.key !== "video" ? c : { ...c,
    renderCell: (r) => <div>{c.renderCell(r)}{lines(r).filter((x) => x.error).map((x) => (
      <div key={x.id}><span className="err">{lines(r).length > 1 ? `${x.account_name}: ` : ""}{x.error}</span></div>))}</div> })
    .concat({ key: "actions", header: "Action", width: pixel(90), renderCell: (r) => actions(r) })
}

export default function HistoryTable({ items, actions }) {
  if (!items.length) return <Text color="secondary">No posts yet. Publish one above.</Text>
  return <Table data={items} columns={actions ? withActions(actions) : base} density="balanced" dividers="rows" hasHover idKey="id" />
}
