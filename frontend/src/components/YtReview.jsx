// Step: the YouTube details. Everything the AI wrote is editable; title options are one click.
import { Badge } from "@astryxdesign/core/Badge"
import { Text } from "@astryxdesign/core/Text"
import { TextArea } from "@astryxdesign/core/TextArea"
import { TextInput } from "@astryxdesign/core/TextInput"
import { DESC_MAX, TITLE_MAX } from "../lib/yt.js"

const Count = ({ n, max }) => <Text size="sm" color={n > max ? "error" : "secondary"}>{n} / {max}</Text>

export default function YtReview({ f, setF, yt, aiDone }) {
  const set = (k) => (v) => setF({ ...f, [k]: v })
  return (
    <div className="stack">
      <div className="platform-head">
        <Text weight="semibold">YouTube details</Text>
        {aiDone && <Badge variant="info" label="AI draft - edit freely" />}
      </div>
      {yt?.titles?.length > 1 && (
        <div>
          <Text size="sm" weight="semibold">Title options (click to use)</Text>
          <div className="chips">
            {yt.titles.map((t) => (
              <button type="button" key={t} className={`chip${f.title === t ? " chip--on" : ""}`} onClick={() => set("title")(t)}>{t}</button>
            ))}
          </div>
        </div>
      )}
      <TextInput label="Title" isRequired value={f.title} onChange={set("title")} />
      <Count n={f.title.length} max={TITLE_MAX} />
      <TextArea label="Description" rows={10} value={f.description} onChange={set("description")} />
      <Count n={f.description.length} max={DESC_MAX} />
      <TextInput label="Tags" value={f.tags} onChange={set("tags")} placeholder="water, dubai, saving" />
      {yt && (
        <div className="tips">
          <Text size="sm" weight="semibold">What the AI suggests</Text>
          <Text size="sm"><b>Post type:</b> {yt.format === "short" ? "YouTube Short" : "Normal video"}. {yt.format_reason}</Text>
          <Text size="sm"><b>Category:</b> {yt.category_name}{yt.category_reason ? `. ${yt.category_reason}` : ""}</Text>
          {yt.hashtags.length > 0 && <Text size="sm"><b>Hashtags:</b> {yt.hashtags.map((h) => `#${h}`).join(" ")} (the first three show above the title)</Text>}
          {yt.thumbnail_ideas.length > 0 && (
            <div><Text size="sm"><b>Thumbnail ideas:</b></Text>
              <ul className="help">{yt.thumbnail_ideas.map((t) => <li key={t}>{t}</li>)}</ul></div>
          )}
        </div>
      )}
    </div>
  )
}
