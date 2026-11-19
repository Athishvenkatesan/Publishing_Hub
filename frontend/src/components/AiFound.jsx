// "What the AI found": the plain description of the video plus its facts, shared by both upload screens.
import { Text } from "@astryxdesign/core/Text"

export default function AiFound({ meta, description, note }) {
  const mins = Math.floor(meta.duration_s / 60), secs = Math.round(meta.duration_s % 60)
  const short = meta.orientation === "vertical" && meta.duration_s <= 180
  return (
    <div className="found">
      <Text weight="semibold" size="sm">What the AI found</Text>
      <Text size="sm">{description}</Text>
      <Text size="sm" color="secondary">
        {mins}:{String(secs).padStart(2, "0")} - {meta.orientation} {meta.width}x{meta.height} - {meta.has_audio ? "has sound" : "no sound"}
        {note ? ` - ${note}` : short ? " - posts as a YouTube Short / Instagram Reel" : " - posts as a normal video"}
      </Text>
    </div>
  )
}
