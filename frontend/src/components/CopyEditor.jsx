import { Badge } from "@astryxdesign/core/Badge"
import { CheckboxList, CheckboxListItem } from "@astryxdesign/core/CheckboxList"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { TextInput } from "@astryxdesign/core/TextInput"
import { LIMITS } from "../lib/copy.js"

const Count = ({ n, max }) => <Text size="sm" color={n > max ? "error" : "secondary"}>{n} / {max}</Text>

function Accounts({ list, picked, setPicked }) {
  return (
    <CheckboxList label="Post to" value={picked} onChange={setPicked} density="compact">
      {list.map((a) => <CheckboxListItem key={a.id} value={a.id} isDisabled={!a.active}
        label={`@${a.username}${a.active ? "" : " (reconnect needed)"}`} />)}
    </CheckboxList>
  )
}

function Instagram({ c, set, ...acc }) {
  const total = (c.caption + "\n\n" + c.hashtags).length
  return (
    <>
      <Accounts {...acc} />
      <TextArea label="Caption" value={c.caption} rows={3} onChange={(v) => set({ ...c, caption: v })} />
      <TextInput label="Hashtags" value={c.hashtags} onChange={(v) => set({ ...c, hashtags: v })} placeholder="#water #dubai" />
      <Count n={total} max={LIMITS.igCaption} />
    </>
  )
}

function YouTube({ c, set, ...acc }) {
  return (
    <>
      <Accounts {...acc} />
      <TextInput label="Title" value={c.title} onChange={(v) => set({ ...c, title: v })} isRequired />
      <Count n={c.title.length} max={LIMITS.ytTitle} />
      <TextArea label="Description" value={c.description} rows={4} onChange={(v) => set({ ...c, description: v })} />
      <TextInput label="Tags" value={c.tags} onChange={(v) => set({ ...c, tags: v })} placeholder="water, dubai, saving" />
      <SegmentedControl layout="fill" label="Who can watch" value={c.visibility} onChange={(v) => set({ ...c, visibility: v })}>
        <SegmentedControlItem value="public" label="Public" />
        <SegmentedControlItem value="unlisted" label="Unlisted" />
        <SegmentedControlItem value="private" label="Private" />
      </SegmentedControl>
    </>
  )
}

const PLATFORMS = { instagram: { name: "Instagram", View: Instagram }, youtube: { name: "YouTube", View: YouTube } }

export default function CopyEditor({ accounts, picked, setPicked, copy, setCopy, aiDone }) {
  const platforms = [...new Set(accounts.map((a) => a.platform))].filter((p) => PLATFORMS[p])
  if (!platforms.length) return <Text color="secondary">No connected accounts found.</Text>
  return (
    <div className="platforms">
      {platforms.map((p) => {
        const list = accounts.filter((a) => a.platform === p)
        const ids = list.map((a) => a.id)
        const { name, View } = PLATFORMS[p]
        return (
          <section key={p} className="platform">
            <header className="platform-head">
              <Text weight="semibold">{name}</Text>
              {aiDone && <Badge variant="info" label="AI draft - edit freely" />}
            </header>
            <View c={copy[p]} set={(v) => setCopy({ ...copy, [p]: v })} list={list}
              picked={picked.filter((x) => ids.includes(x))}
              setPicked={(sel) => setPicked([...picked.filter((x) => !ids.includes(x)), ...sel])} />
          </section>
        )
      })}
    </div>
  )
}
