// Step: the X post. The AI writes three short options; one click uses one, and everything stays editable.
import { Badge } from "@astryxdesign/core/Badge"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { TEXT_SOFT } from "../lib/x.js"

export default function XReview({ f, setF, draft, aiDone }) {
  const n = f.text.length
  return (
    <div className="stack">
      <div className="platform-head">
        <Text weight="semibold">X post</Text>
        {aiDone && <Badge variant="info" label="AI draft - edit freely" />}
      </div>
      {draft?.options?.length > 1 && (
        <div>
          <Text size="sm" weight="semibold">Post options (click to use)</Text>
          <div className="chips">
            {draft.options.map((o) => <button type="button" key={o} className={`chip${f.text === o ? " chip--on" : ""}`} onClick={() => setF({ ...f, text: o })}>{o}</button>)}
          </div>
        </div>
      )}
      <TextArea label="Post text" isRequired rows={6} value={f.text} onChange={(v) => setF({ ...f, text: v })} />
      <Text size="sm" color={n > TEXT_SOFT ? "error" : "secondary"}>{n} / {TEXT_SOFT}{n > TEXT_SOFT ? " - only Premium accounts can post this much; X refuses it on a normal account" : ""}</Text>
      <div className="tips">
        <Text size="sm" weight="semibold">Good to know</Text>
        <Text size="sm">Links count as 23 characters on X. Words starting with # become hashtags.</Text>
        <Text size="sm">X's API has no editing: to change a post later, delete it and post again.</Text>
      </div>
    </div>
  )
}
