// The three-dot menu on a LinkedIn or X history row. A video posted to several accounts is one row: each action asks which account first.
import { MoreMenu } from "@astryxdesign/core/MoreMenu"

export default function LiRowMenu({ row, onAct, site = "LinkedIn", canEdit = true }) {
  const link = (row.rows || [row]).some((r) => r.post_url)
  const items = [
    { label: `Open on ${site}`, isDisabled: !link, onClick: () => onAct("open", row) },
    { label: "Copy link", isDisabled: !link, onClick: () => onAct("copy", row) },
    ...(canEdit ? [{ type: "divider" }, { label: "Edit the post text", onClick: () => onAct("edit", row) }] : []),
    { type: "divider" },
    { label: "Remove from this list", onClick: () => onAct("remove", row) },
    { label: `Delete from ${site}...`, onClick: () => onAct("delete", row) },
  ]
  return <MoreMenu items={items} label={`Actions for ${row.title || row.filename}`} />
}
