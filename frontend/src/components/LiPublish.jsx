// Step: who sees it, where it goes, and the Post button. LinkedIn has no scheduled posting in its public API, so it always posts now.
import { Button } from "@astryxdesign/core/Button"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"

export default function LiPublish({ f, setF, picker, busy, problem, onPublish, count, summary }) {
  return (
    <div className="stack">
      {picker}
      <SegmentedControl label="Who can see it" value={f.visibility} onChange={(v) => setF({ ...f, visibility: v })}>
        <SegmentedControlItem value="PUBLIC" label="Anyone" />
        <SegmentedControlItem value="CONNECTIONS" label="Connections only" />
      </SegmentedControl>
      <Text size="sm" color="secondary">It posts right away. LinkedIn does not allow scheduled posts from apps.</Text>
      <Button size="lg" label={"Post to LinkedIn" + (count > 1 ? ` (${count} accounts)` : "")} isLoading={busy} isDisabled={!!problem || busy} onClick={onPublish} />
      {!problem && summary && <Text size="sm" weight="semibold">{summary}</Text>}
      {problem && <Text size="sm" color="secondary">{problem}</Text>}
      {busy && <Text size="sm" color="secondary">Uploading to LinkedIn. A large video can take a few minutes.</Text>}
    </div>
  )
}
