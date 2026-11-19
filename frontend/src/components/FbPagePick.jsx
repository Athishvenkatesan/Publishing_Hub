// Which Facebook Page to post to. One Page: just its name. Several: a switch.
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"

export const postablePages = (pages) => pages.filter((p) => p.tasks.includes("CREATE_CONTENT"))

export default function FbPagePick({ pages, value, onChange }) {
  const list = postablePages(pages)
  if (list.length === 1) return <Text size="sm">Posting to <b>{list[0].name}</b></Text>
  if (list.length < 2) return null
  return (
    <SegmentedControl label="Page" value={value} onChange={onChange}>
      {list.map((p) => <SegmentedControlItem key={p.id} value={p.id} label={p.name} />)}
    </SegmentedControl>
  )
}
