// Step: the LinkedIn post. Everything the AI wrote is editable; the opening lines are one click.
import { Badge } from "@astryxdesign/core/Badge"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { TextInput } from "@astryxdesign/core/TextInput"
import { TEXT_MAX, TITLE_MAX, withHook } from "../lib/li.js"

const Count = ({ n, max }) => <Text size="sm" color={n > max ? "error" : "secondary"}>{n} / {max}</Text>

export default function LiReview({ f, setF, draft: li, aiDone }) {
  const set = (k) => (v) => setF({ ...f, [k]: v })
  return (
    <div className="stack">
      <div className="platform-head">
        <Text weight="semibold">LinkedIn post</Text>
        {aiDone && <Badge variant="info" label="AI draft - edit freely" />}
      </div>
      {li?.hooks?.length > 1 && (
        <div>
          <Text size="sm" weight="semibold">Opening line options (click to use)</Text>
          <div className="chips">
            {li.hooks.map((h) => <button type="button" key={h} className={`chip${f.text.startsWith(h) ? " chip--on" : ""}`} onClick={() => set("text")(withHook(li, h))}>{h}</button>)}
          </div>
        </div>
      )}
      <TextArea label="Post text" isRequired rows={12} value={f.text} onChange={set("text")} />
      <Count n={f.text.length} max={TEXT_MAX} />
      <TextInput label="Video title" isOptional value={f.title} onChange={set("title")} placeholder="Shown with the video" />
      <Count n={f.title.length} max={TITLE_MAX} />
      <div className="tips">
        <Text size="sm" weight="semibold">Good to know</Text>
        <Text size="sm">LinkedIn shows only the first few lines before "see more", so the opening line matters most.</Text>
        <Text size="sm">Words starting with # become hashtags. Characters like ( ) @ _ are sent as plain text, so they never cut the post short.</Text>
      </div>
    </div>
  )
}
