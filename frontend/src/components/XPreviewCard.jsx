// "How it will look" on X: the name, the text and the video.
import { Text } from "@astryxdesign/core/Text"

export default function XPreviewCard({ video, text, name }) {
  return (
    <div className="pv pv--x">
      <div className="pv-body">
        <Text weight="semibold">{name || "Your account"}</Text>
        <p className="pv-text">{text || "Your post text appears here"}</p>
      </div>
      {video && <div className="pv-media"><video src={video} muted /></div>}
    </div>
  )
}
