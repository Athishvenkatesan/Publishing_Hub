// Channel profile, headline numbers, feature status and shortcuts into YouTube Studio.
import { useState } from "react"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { studioOverview, studioReports } from "../lib/api.js"
import { compact, duration, longDate } from "../lib/format.js"
import { useLoad } from "../lib/useLoad.js"
import StatTile from "./charts/StatTile.jsx"

const LINKS = [["dashboard", "Studio dashboard"], ["content", "Content"], ["analytics", "Analytics"], ["comments", "Comments"], ["playlists", "Playlists"]]

function Last28({ account }) {
  const { data } = useLoad(() => studioReports(28), [account])
  if (!data?.available) return null
  const t = data.totals, p = data.previous
  return (
    <div className="stack">
      <Text weight="semibold">Last 28 days</Text>
      <div className="tiles">
        <StatTile label="Views" value={compact(t.views)} cur={t.views} prev={p.views} />
        <StatTile label="Watch time (hours)" value={compact(t.watchHours)} cur={t.watchHours} prev={p.watchHours} />
        <StatTile label="Net subscribers" value={compact(t.netSubscribers)} cur={t.netSubscribers} prev={p.netSubscribers} />
        <StatTile label="Average view duration" value={duration(t.averageViewDuration || 0)} cur={t.averageViewDuration} prev={p.averageViewDuration} />
      </div>
    </div>
  )
}

export default function StudioOverview({ account, goto }) {
  const { data, error, loading } = useLoad(studioOverview, [account])
  const [noAvatar, setNoAvatar] = useState(false)
  if (error) return <Banner status="error" title="Could not read the channel" description={error} />
  if (!data) return <div className="working"><Spinner /><Text size="sm">Reading your channel from YouTube...</Text></div>
  const c = data.channel
  if (!c) return <Banner status="warning" title="No channel found" description="This Google account has no YouTube channel yet. Create one on YouTube, then reload." />
  const ver = c.long_uploads === "allowed"
  return (
    <div className={`stack${loading ? " is-loading" : ""}`}>
      <section className="panel">
        <div className="chan">
          {c.avatar && !noAvatar ? <img className="chan-img" src={c.avatar} alt="" referrerPolicy="no-referrer" onError={() => setNoAvatar(true)} /> : <span className="dot dot--youtube">Y</span>}
          <div className="chan-main">
            <Text weight="semibold" size="lg">{c.title}</Text>
            <Text size="sm" color="secondary">{c.handle} - created {longDate(c.created)}{c.country ? ` - ${c.country}` : ""}</Text>
            {c.description && <Text size="sm">{c.description.slice(0, 280)}</Text>}
            {c.keywords && <Text size="sm" color="secondary">Keywords: {c.keywords}</Text>}
          </div>
        </div>
        <div className="tiles">
          <StatTile label="Subscribers" value={c.subscribers == null ? "Hidden" : compact(c.subscribers)} />
          <StatTile label="Total views" value={compact(c.views)} />
          <StatTile label="Public videos" value={compact(c.videos)} />
        </div>
      </section>
      {data.reports_permission ? <Last28 account={account} /> : (
        <Banner status="info" title="Reports are not switched on for this account" description="The Reports tab needs the analytics permission. Open the Access tab to add it." />
      )}
      <section className="panel">
        <Text weight="semibold">Channel status</Text>
        <ul className="status-list">
          <li><Badge variant={ver ? "success" : "warning"} label={ver ? "Verified" : "Not verified"} />
            <Text size="sm">{ver ? "Custom thumbnails and videos over 15 minutes are unlocked." : "YouTube blocks custom thumbnails and long videos until you verify the channel by phone."}</Text>
            {!ver && <a className="linkbtn" href="https://www.youtube.com/verify" target="_blank" rel="noreferrer">Verify on YouTube</a>}</li>
          <li><Badge variant="neutral" label={c.privacy || "unknown"} /><Text size="sm">Channel visibility</Text></li>
          <li><Badge variant="neutral" label={c.made_for_kids ? "Made for kids" : "Not made for kids"} /><Text size="sm">Audience setting</Text></li>
          <li><Badge variant={c.is_linked ? "success" : "warning"} label={c.is_linked ? "Linked" : "Not linked"} /><Text size="sm">Channel is linked to a YouTube identity, needed to upload.</Text></li>
        </ul>
      </section>
      <section className="panel">
        <Text weight="semibold">Open in YouTube Studio</Text>
        <Text size="sm" color="secondary">Some things only YouTube Studio can do, such as the people with access to the channel, comments and monetization.</Text>
        <div className="row-btns">{LINKS.map(([k, name]) => <a key={k} className="btn-link btn-link--ghost" href={c.links[k]} target="_blank" rel="noreferrer">{name}</a>)}
          <button type="button" className="btn-link btn-link--ghost" onClick={() => goto("access")}>Permissions of this app</button></div>
      </section>
    </div>
  )
}
