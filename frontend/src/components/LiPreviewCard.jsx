// "How it will look" on LinkedIn: the poster's name, the first lines of the text and the video.
import { Text } from "@astryxdesign/core/Text"

export default function LiPreviewCard({ video, text, name, visibility }) {
  const lines = (text || "").split("\n").filter(Boolean).slice(0, 3).join("\n")
  return (
    <div className="pv pv--linkedin">
      <div className="pv-body">
        <Text weight="semibold">{name || "Your name"}</Text>
        <Text size="sm" color="secondary">Just now - {visibility === "CONNECTIONS" ? "Connections" : "Anyone"}</Text>
        <p className="pv-text">{lines || "Your post text appears here"}{(text || "").length > lines.length ? " ...see more" : ""}</p>
      </div>
      {video && <div className="pv-media"><video src={video} muted /></div>}
    </div>
  )
}
