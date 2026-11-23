// Slide-in panel (not a popup): a video was posted to several channels, so ask which one the chosen action is for.
import { Badge } from "@astryxdesign/core/Badge"
import { Button } from "@astryxdesign/core/Button"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"

const LABELS = { open: "Open on YouTube", copy: "Copy link", edit: "Edit title, description, tags", schedule: "Reschedule", cancel: "Cancel schedule (keep private)",
  public: "Set visibility: Public", unlisted: "Set visibility: Unlisted", private: "Set visibility: Private", remove: "Remove from this list", delete: "Delete from YouTube" }
const STATE = { PUBLISHED: "Published", SCHEDULED: "Scheduled", PUBLISHING: "Publishing...", FAILED: "Failed", CANCELLED: "Cancelled" }

// Why a channel cannot take this action (shown instead of letting it fail).
const blocked = (kind, r) => (["open", "copy"].includes(kind) && !r.post_url ? "No link yet" : ["schedule", "cancel"].includes(kind) && r.status !== "SCHEDULED" ? "Not scheduled" : "")

export default function YtChannelAsk({ ask, onPick, onClose, noun = "channel", labels = {} }) {
  const { kind, row } = ask || {}
  const text = { ...LABELS, ...labels }
  return (
    <>
      <div className={`scrim${ask ? " scrim--on" : ""}`} onClick={onClose} />
      <aside className={`drawer${ask ? " drawer--on" : ""}`} aria-hidden={!ask}>
        <header className="drawer-head">
          <div><Heading level={3}>Which {noun}?</Heading>
            <Text size="sm" color="secondary">{text[kind]}: {row?.title || row?.filename}</Text></div>
          <Button variant="secondary" size="sm" label="Close" onClick={onClose} />
        </header>
        <div className="accts" role="list">
          {(row?.rows || []).map((r) => { const why = blocked(kind, r)
            return (
              <button type="button" key={r.id} className="acct" disabled={!!why} onClick={() => onPick(r)}>
                <span className="acct-label">{r.account_name}</span>
                <span className="acct-state">{why ? <Badge variant="neutral" label={why} /> : STATE[r.status] || r.status}</span>
              </button>
            )
          })}
        </div>
        <Text size="sm" color="secondary">The same video is on each of these {noun}s. The action only changes the one you pick.</Text>
      </aside>
    </>
  )
}
