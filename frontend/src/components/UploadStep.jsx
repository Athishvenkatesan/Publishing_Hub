import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { TextInput } from "@astryxdesign/core/TextInput"
import AiFound from "./AiFound.jsx"
import FilePick from "./FilePick.jsx"

const MAX_MB = 300

export default function UploadStep({ file, preview, onFile, lang, setLang, hint, setHint, ai, found, onAnalyze }) {
  return (
    <div className="stack">
      <FilePick label="Video clip" value={file} onChange={onFile}
        accept="video/mp4,video/quicktime" maxMB={MAX_MB}
        description={`MP4 or MOV, up to ${MAX_MB} MB. Vertical 9:16 works best.`} />
      {preview && <video className="preview" src={preview} controls muted />}
      <SegmentedControl layout="fill" label="Language of the text" value={lang} onChange={setLang}>
        <SegmentedControlItem value="en" label="English" />
        <SegmentedControlItem value="ar" label="Arabic" />
        <SegmentedControlItem value="both" label="Both" />
      </SegmentedControl>
      <TextInput label="Context for the AI" isOptional value={hint} onChange={setHint}
        placeholder="e.g. Ramadan water saving campaign" />
      {ai.state === "off" && <Banner status="warning" title="Local AI is not ready" description={ai.reason} />}
      {ai.state === "working" && (
        <div className="working"><Spinner /><Text size="sm">Your local model is watching the video and writing the text. This takes about a minute.</Text></div>
      )}
      {ai.state === "error" && <Banner status="error" title="Could not analyse the video" description={ai.reason} />}
      {found && <AiFound {...found} />}
      {file && ai.state !== "working" && (
        <div><Button variant="secondary" label={ai.state === "done" ? "Regenerate text" : "Analyse video"} onClick={onAnalyze} /></div>
      )}
    </div>
  )
}
