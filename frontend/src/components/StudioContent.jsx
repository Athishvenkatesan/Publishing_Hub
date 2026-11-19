// Every video on the channel with its visibility, schedule and numbers. Read-only here; each row opens in YouTube Studio.
import { useEffect, useMemo, useState } from "react"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { TextInput } from "@astryxdesign/core/TextInput"
import { studioUrl, studioVideos } from "../lib/api.js"
import { compact, duration, longDate } from "../lib/format.js"

const kind = (v) => (v.privacy === "private" && v.publish_at ? "scheduled" : v.privacy || "private")
const BADGE = { public: ["success", "Public"], unlisted: ["neutral", "Unlisted"], private: ["warning", "Private"], scheduled: ["info", "Scheduled"] }

export default function StudioContent({ account }) {
  const [items, setItems] = useState([])
  const [next, setNext] = useState("")
  const [total, setTotal] = useState(0)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState("")
  const [filter, setFilter] = useState("all")
  const [q, setQ] = useState("")

  async function load(token = "", replace = false) {
    setBusy(true); setError("")
    try {
      const d = await studioVideos(token)
      setItems((cur) => (replace ? d.items : [...cur, ...d.items])); setNext(d.next || ""); setTotal(d.total)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  useEffect(() => { setItems([]); load("", true) }, [account])  // eslint-disable-line react-hooks/exhaustive-deps

  const shown = useMemo(() => items.filter((v) => (filter === "all" || kind(v) === filter) && (!q.trim() || v.title.toLowerCase().includes(q.trim().toLowerCase()))), [items, filter, q])
  return (
    <section className="panel">
      <div className="panel-head">
        <Text weight="semibold">Content ({total || items.length})</Text>
        <a className="linkbtn" href={studioUrl("videos.csv")}>Download CSV</a>
      </div>
      <div className="filters">
        <TextInput label="Search titles" value={q} onChange={setQ} />
        <SegmentedControl label="Show" value={filter} onChange={setFilter}>
          <SegmentedControlItem value="all" label="All" /><SegmentedControlItem value="public" label="Public" /><SegmentedControlItem value="scheduled" label="Scheduled" />
          <SegmentedControlItem value="private" label="Private" /><SegmentedControlItem value="unlisted" label="Unlisted" />
        </SegmentedControl>
      </div>
      {error && <Banner status="error" title="Could not load videos" description={error} />}
      <div className="table-wrap tall">
        <table className="mini data">
          <thead><tr><th>Video</th><th>Visibility</th><th>Date</th><th>Views</th><th>Likes</th><th>Comments</th><th></th></tr></thead>
          <tbody>
            {shown.map((v) => {
              const [variant, label] = BADGE[kind(v)] || BADGE.private
              return (
                <tr key={v.id}>
                  <td><div className="vid"><span className="vid-thumb">{v.thumb && <img src={v.thumb} alt="" referrerPolicy="no-referrer" onError={(e) => { e.currentTarget.style.display = "none" }} />}</span><div><div className="vid-title">{v.title}</div><span className="muted">{duration(v.duration_s)}</span></div></div></td>
                  <td><Badge variant={variant} label={label} /></td>
                  <td>{longDate(v.publish_at || v.published_at)}</td><td>{compact(v.views)}</td><td>{compact(v.likes)}</td><td>{compact(v.comments)}</td>
                  <td><div className="acts"><a className="linkbtn" href={v.url} target="_blank" rel="noreferrer">Watch</a><a className="linkbtn" href={v.studio_url} target="_blank" rel="noreferrer">Edit in Studio</a></div></td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!busy && !shown.length && <p className="muted pad">No videos match.</p>}
      </div>
      <div className="row-btns">
        {busy && <Spinner />}
        {next && !busy && <Button variant="secondary" label="Load more" onClick={() => load(next)} />}
      </div>
    </section>
  )
}
