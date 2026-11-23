// Step: who can reply, where it goes, and the Post button. X's API has no scheduled posting, so it always posts now.
import { Button } from "@astryxdesign/core/Button"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"

export default function XPublish({ f, setF, picker, busy, problem, onPublish, count, summary }) {
  return (
    <div className="stack">
      {picker}
      <SegmentedControl label="Who can reply" value={f.reply} onChange={(v) => setF({ ...f, reply: v })}>
        <SegmentedControlItem value="everyone" label="Everyone" />
        <SegmentedControlItem value="following" label="People you follow" />
        <SegmentedControlItem value="mentionedUsers" label="Only mentioned" />
      </SegmentedControl>
      <Text size="sm" color="secondary">It posts right away (X does not allow scheduled posts from apps). Each post uses X API credits, about $0.015.</Text>
      <Button size="lg" label={"Post to X" + (count > 1 ? ` (${count} accounts)` : "")} isLoading={busy} isDisabled={!!problem || busy} onClick={onPublish} />
      {!problem && summary && <Text size="sm" weight="semibold">{summary}</Text>}
      {problem && <Text size="sm" color="secondary">{problem}</Text>}
      {busy && <Text size="sm" color="secondary">Uploading to X. A large video can take a few minutes.</Text>}
    </div>
  )
}
