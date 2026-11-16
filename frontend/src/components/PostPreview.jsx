// Live look-alike of how the post will appear, so the user can check before pressing the button.
import { Text } from "@astryxdesign/core/Text"

export default function PostPreview({ platform, handle, copy, src }) {
  const ig = platform === "instagram"
  const text = ig ? [copy.caption, copy.hashtags].filter(Boolean).join("\n\n") : copy.description
  return (
    <div className={`pv pv--${platform}`}>
      <div className="pv-media">{src ? <video src={src} muted /> : <span>Video</span>}
        <span className="pv-tag">{ig ? "Reel" : "YouTube"}</span></div>
      <div className="pv-body">
        {!ig && <Text weight="semibold">{copy.title || "Your title appears here"}</Text>}
        <Text size="sm" color="secondary">@{handle}</Text>
        <p className="pv-text">{text || "Your text appears here."}</p>
      </div>
    </div>
  )
}
