// Step: the Facebook post. Everything the AI wrote is editable; the title options are one click.
import { Badge } from "@astryxdesign/core/Badge"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { TextInput } from "@astryxdesign/core/TextInput"
import { CAPTION_MAX, TEXT_MAX, TITLE_MAX } from "../lib/meta.js"

const Count = ({ n, max }) => <Text size="sm" color={n > max ? "error" : "secondary"}>{n} / {max}</Text>

export default function MetaReview({ f, setF, draft, aiDone, showCaption }) {
  const set = (k) => (v) => setF({ ...f, [k]: v })
  return (
    <div className="stack">
      <div className="platform-head">
        <Text weight="semibold">{showCaption ? "Facebook, Instagram and Threads post" : "Facebook video post"}</Text>
        {aiDone && <Badge variant="info" label="AI draft - edit freely" />}
      </div>
      {draft?.titles?.length > 1 && (
        <div>
          <Text size="sm" weight="semibold">Title options (click to use)</Text>
          <div className="chips">
            {draft.titles.map((t) => <button type="button" key={t} className={`chip${f.title === t ? " chip--on" : ""}`} onClick={() => set("title")(t)}>{t}</button>)}
          </div>
        </div>
      )}
      <TextInput label="Video title" value={f.title} onChange={set("title")} placeholder="Shown above the video" />
      <Count n={f.title.length} max={TITLE_MAX} />
      <TextArea label="Post text" rows={10} value={f.text} onChange={set("text")} />
      <Count n={f.text.length} max={TEXT_MAX} />
      {showCaption && (
        <>
          <TextArea label="Instagram and Threads caption" rows={5} value={f.caption} onChange={set("caption")} />
          <Count n={f.caption.length} max={CAPTION_MAX} />
        </>
      )}
    </div>
  )
}
