// The three-dot menu on a YouTube history row. The items depend on the video's state.
import { MoreMenu } from "@astryxdesign/core/MoreMenu"

export default function YtRowMenu({ row, onAct }) {
  const rows = row.rows || [row]  // a video posted to several channels is one row: each action asks which channel
  const scheduled = rows.some((r) => r.status === "SCHEDULED")
  const link = rows.some((r) => r.post_url)
  const items = [
    { label: "Open on YouTube", isDisabled: !link, onClick: () => onAct("open", row) },
    { label: "Copy link", isDisabled: !link, onClick: () => onAct("copy", row) },
    { type: "divider" },
    { label: "Edit title, description, tags", onClick: () => onAct("edit", row) },
    ...(scheduled ? [
      { label: "Reschedule", onClick: () => onAct("schedule", row) },
      { label: "Cancel schedule (keep private)", onClick: () => onAct("cancel", row) },
    ] : []),
    { label: "Set visibility: Public", onClick: () => onAct("public", row) },
    { label: "Set visibility: Unlisted", onClick: () => onAct("unlisted", row) },
    { label: "Set visibility: Private", onClick: () => onAct("private", row) },
    { type: "divider" },
    { label: "Remove from this list", onClick: () => onAct("remove", row) },
    { label: "Delete from YouTube...", onClick: () => onAct("delete", row) },
  ]
  return <MoreMenu items={items} label={`Actions for ${row.title || row.filename}`} />
}
