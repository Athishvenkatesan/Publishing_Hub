// "How it will look" on YouTube: the thumbnail with the title and channel under it.
import { Text } from "@astryxdesign/core/Text"

export default function YtPreviewCard({ thumb, title, channel, short }) {
  return (
    <div className="pv pv--youtube">
      <div className="pv-media">
        {thumb ? <img src={thumb} alt="" /> : <span>Thumbnail</span>}
        <span className="pv-tag">{short ? "Short" : "YouTube"}</span>
      </div>
      <div className="pv-body">
        <Text weight="semibold">{title || "Your title appears here"}</Text>
        <Text size="sm" color="secondary">{channel || "Your channel"} - Just now</Text>
      </div>
    </div>
  )
}
