// Thumbnail maker: the local model picks the best frames and writes headlines; the user can still change everything.
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { TextInput } from "@astryxdesign/core/TextInput"

export default function YtThumbs({ th, file, onRegenerate, unverified, verifyUrl }) {
  if (!file) return null
  return (
    <section className="thumbs">
      <div className="platform-head">
        <Text weight="semibold">Thumbnail</Text>
        {th.status === "done" && <Badge variant="info" label={th.rankedBy === "ai" ? "AI picked the frames" : "Sharpest frames"} />}
      </div>
      {unverified && (
        <Banner status="warning" title="Your channel can't use custom thumbnails yet"
          description="YouTube unlocks custom thumbnails after the channel is phone-verified, so this thumbnail is not sent by default. You can still design it and download the JPG, then set it in YouTube Studio once the channel is verified." />
      )}
      {unverified && <a className="btn-link btn-link--ghost" href={verifyUrl || "https://www.youtube.com/verify"} target="_blank" rel="noreferrer">Verify my channel on YouTube</a>}
      {th.status === "working" && <div className="working"><Spinner /><Text size="sm">Choosing the best frames and writing headlines. This takes about a minute.</Text></div>}
      {th.status === "error" && <Banner status="error" title="Could not make thumbnails" description={th.error} />}
      {th.status === "done" && (
        <>
          <div className="thumb-main">
            {th.preview ? <img src={th.preview} alt="Thumbnail preview" /> : <div className="thumb-wait"><Spinner /></div>}
            {th.rendering && th.preview && <span className="thumb-busy"><Spinner /></span>}
          </div>
          <div className="thumb-grid">
            {th.candidates.map((c, i) => (
              <button type="button" key={c.id} className={`thumb-opt${th.picked === c.id ? " thumb-opt--on" : ""}`} onClick={() => th.setPicked(c.id)}
                aria-label={`Use frame ${i + 1} at ${c.t} seconds`}>
                <img src={c.image} alt="" /><span>Frame at {c.t}s</span>
              </button>
            ))}
          </div>
          {th.note && <Text size="sm" color="secondary">Why this frame: {th.note}</Text>}
          <TextInput label="Headline on the thumbnail" isOptional value={th.headline} onChange={(v) => th.setHeadline(v.slice(0, 60))}
            placeholder="Four words or fewer works best" />
          {th.headlines.length > 1 && (
            <div className="chips chips--row">
              {th.headlines.map((h) => <button type="button" key={h} className={`chip${th.headline === h ? " chip--on" : ""}`} onClick={() => th.setHeadline(h)}>{h}</button>)}
            </div>
          )}
          <SegmentedControl label="Style" value={th.style} onChange={th.setStyle}>
            <SegmentedControlItem value="band" label="Green strip" />
            <SegmentedControlItem value="scrim" label="Dark overlay" />
            <SegmentedControlItem value="none" label="No text" />
          </SegmentedControl>
          <label className="chk"><input type="checkbox" checked={th.logo} onChange={(e) => th.setLogo(e.target.checked)} /><span><b>Add the DEWA logo</b></span></label>
          <label className="chk"><input type="checkbox" checked={th.enabled} onChange={(e) => th.toggle(e.target.checked)} />
            <span><b>Use this thumbnail on YouTube</b><br /><Text size="sm" color="secondary">It is added after YouTube finishes processing the video. For Shorts, YouTube may not show a custom thumbnail.</Text></span></label>
          {th.error && <Text size="sm" color="error">{th.error}</Text>}
          <div className="row-btns">
            <Button variant="secondary" label="Regenerate" onClick={onRegenerate} />
            {th.preview && <a className="dl" href={th.preview} download="thumbnail.jpg">Download JPG</a>}
          </div>
        </>
      )}
    </section>
  )
}
