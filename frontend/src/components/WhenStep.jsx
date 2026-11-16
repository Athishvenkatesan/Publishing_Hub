import { Button } from "@astryxdesign/core/Button"
import { DateTimeInput } from "@astryxdesign/core/DateTimeInput"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"
import { TZ, localInZone } from "../lib/time.js"

export default function WhenStep({ mode, setMode, when, setWhen, busy, ready, onPublish, why, summary }) {
  return (
    <div className="stack">
      <SegmentedControl layout="fill" size="lg" label="When" value={mode} onChange={setMode}>
        <SegmentedControlItem value="now" label="Publish now" />
        <SegmentedControlItem value="schedule" label="Schedule" />
      </SegmentedControl>
      {mode === "schedule" && (
        <div>
          <DateTimeInput className="when-dt" label="Date and time" value={when} onChange={setWhen} min={localInZone()} hourFormat="24h" timeIncrement={5} />
          <Text size="sm" color="secondary">Time zone: {TZ} (UTC+4)</Text>
        </div>
      )}
      <Button size="lg" label={mode === "now" ? "Publish" : "Schedule post"} isLoading={busy} isDisabled={!ready || busy} onClick={onPublish} />
      {ready && summary && <Text size="sm" weight="semibold">{summary}{mode === "schedule" && when ? ` ${when.replace("T", " ")} (${TZ}).` : ""}</Text>}
      {!ready && why && <Text size="sm" color="secondary">{why}</Text>}
      {busy && mode === "now" && <Text size="sm" color="secondary">Instagram processes the video first. This can take a minute.</Text>}
      {mode === "schedule" && <Text size="sm" color="secondary">Instagram posts at the set time. YouTube uploads straight away, with the visibility you chose.</Text>}
    </div>
  )
}
