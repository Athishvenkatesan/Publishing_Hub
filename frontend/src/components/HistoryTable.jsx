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

const base = [
  { key: "when", header: "When", width: pixel(150),
    renderCell: (r) => <Text size="sm">{r.mode === "schedule" ? fmt(r.scheduled_for, r.timezone) : fmt(r.created_at)}</Text> },
  { key: "video", header: "Video", width: proportional({ minWidth: 150 }),
    renderCell: (r) => <div><div><Text weight="semibold" size="sm">{r.title || r.filename}</Text></div>
      {r.caption && <div><Text size="sm" color="secondary">{r.caption.slice(0, 70)}</Text></div>}</div> },
  { key: "account", header: "Account", width: pixel(170),
    renderCell: (r) => <Text size="sm">{r.platform === "youtube-direct" ? `YouTube - ${r.account_name}` : `${r.platform} - @${r.account_name}`}</Text> },
  { key: "status", header: "Status", width: pixel(230),
    renderCell: (r) => { const s = STATUS[r.status] || STATUS.SCHEDULED
      return <Badge variant={s.variant} label={s.label} /> } },
  { key: "link", header: "Post", width: pixel(180),
    renderCell: (r) => r.post_url
      ? <a href={r.post_url} target="_blank" rel="noreferrer">Open post</a>
      : r.error ? <span className="err">{r.error}</span> : <Text size="sm" color="secondary">-</Text> },
]

// With `actions`, the last column becomes "Action" (a menu per row) and any error note moves under the title.
function withActions(actions) {
  return base.slice(0, -1).map((c) => c.key !== "video" ? c : { ...c,
    renderCell: (r) => <div>{c.renderCell(r)}{r.error && <div><span className="err">{r.error}</span></div>}</div> })
    .concat({ key: "actions", header: "Action", width: pixel(90), renderCell: (r) => actions(r) })
}

export default function HistoryTable({ items, actions }) {
  if (!items.length) return <Text color="secondary">No posts yet. Publish one above.</Text>
  return <Table data={items} columns={actions ? withActions(actions) : base} density="balanced" dividers="rows" hasHover idKey="id" />
}
