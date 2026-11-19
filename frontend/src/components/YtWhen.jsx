// Step: who can watch, when, and the publish button.
import { Button } from "@astryxdesign/core/Button"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"
import { TZ } from "../lib/time.js"
import FbWhen from "./FbWhen.jsx"

export default function YtWhen({ f, setF, mode, setMode, when, setWhen, busy, problem, onPublish, summary, picker = null, count = 1 }) {
  return (
    <div className="stack">
      {picker}
      {mode === "now" && (
        <SegmentedControl label="Who can watch" value={f.privacy} onChange={(v) => setF({ ...f, privacy: v })}>
          <SegmentedControlItem value="public" label="Public" />
          <SegmentedControlItem value="unlisted" label="Unlisted" />
          <SegmentedControlItem value="private" label="Private" />
        </SegmentedControl>
      )}
      <FbWhen mode={mode} setMode={setMode} when={when} setWhen={setWhen}
        note="The video uploads now as private, and YouTube makes it public at that time." />
      <Button size="lg" label={(mode === "now" ? "Upload to YouTube" : "Schedule on YouTube") + (count > 1 ? ` (${count} channels)` : "")} isLoading={busy} isDisabled={!!problem || busy} onClick={onPublish} />
      {!problem && summary && <Text size="sm" weight="semibold">{summary}{mode === "schedule" && when ? ` ${when.replace("T", " ")} (${TZ}).` : ""}</Text>}
      {problem && <Text size="sm" color="secondary">{problem}</Text>}
      {busy && <Text size="sm" color="secondary">Uploading to YouTube. A large video can take a few minutes.</Text>}
    </div>
  )
}
