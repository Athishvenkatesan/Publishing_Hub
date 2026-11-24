// The three-dot menu on a Facebook / Instagram / Threads history row: just "Open" for each platform the video went to.
// (Copy, edit and delete for Meta posts are not built yet.)
import { MoreMenu } from "@astryxdesign/core/MoreMenu"

const SITE = { facebook: "Facebook", "instagram-meta": "Instagram", threads: "Threads" }

export default function MetaRowMenu({ row }) {
  const rows = row.rows || [row]  // one video on Facebook and Instagram is one row: each platform gets its own Open
  const open = (url) => window.open(url, "_blank", "noopener")
  const withLink = rows.filter((r) => r.post_url)
  const items = withLink.length
    ? withLink.map((r) => ({ label: `Open on ${SITE[r.platform] || r.platform}${rows.length > 1 ? ` - ${r.account_name}` : ""}`, onClick: () => open(r.post_url) }))
    : [{ label: "Open on Meta (no link yet)", isDisabled: true }]
  return <MoreMenu items={items} label={`Actions for ${row.title || row.filename || "this post"}`} />
}
