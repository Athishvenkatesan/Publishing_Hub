// The three-dot menu on a YouTube history row. The items depend on the video's state.
import { MoreMenu } from "@astryxdesign/core/MoreMenu"

export default function YtRowMenu({ row, onAct }) {
  const scheduled = row.status === "SCHEDULED"
  const items = [
    { label: "Open on YouTube", isDisabled: !row.post_url, onClick: () => window.open(row.post_url, "_blank", "noopener") },
    { label: "Copy link", isDisabled: !row.post_url, onClick: () => onAct("copy", row) },
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
