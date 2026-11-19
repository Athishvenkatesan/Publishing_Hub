// Publish now or schedule. Facebook needs 10 minutes to 75 days ahead.
import { DateTimeInput } from "@astryxdesign/core/DateTimeInput"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"
import { TZ, localInZone } from "../lib/time.js"

export default function FbWhen({ mode, setMode, when, setWhen, note = "Facebook needs 10 minutes to 75 days ahead." }) {
  return (
    <>
      <SegmentedControl label="When" value={mode} onChange={setMode}>
        <SegmentedControlItem value="now" label="Publish now" />
        <SegmentedControlItem value="schedule" label="Schedule" />
      </SegmentedControl>
      {mode === "schedule" && (
        <div>
          <DateTimeInput label="Date and time" value={when} onChange={setWhen} min={localInZone(new Date(Date.now() + 11 * 60000))} hourFormat="24h" timeIncrement={5} />
          <Text size="sm" color="secondary">Time zone: {TZ}. {note}</Text>
        </div>
      )}
    </>
  )
}
