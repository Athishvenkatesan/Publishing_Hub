import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { studioPlaylists } from "../lib/api.js"
import { longDate } from "../lib/format.js"
import { useLoad } from "../lib/useLoad.js"

export default function StudioPlaylists({ account }) {
  const { data, error, loading } = useLoad(studioPlaylists, [account])
  return (
    <section className="panel">
      <Text weight="semibold">Playlists ({data?.items.length ?? "..."})</Text>
      {error && <Banner status="error" title="Could not load playlists" description={error} />}
      {loading && !data && <Spinner />}
      {data && !data.items.length && <p className="muted">This channel has no playlists.</p>}
      {data?.items.length > 0 && (
        <div className="table-wrap"><table className="mini data"><thead><tr><th>Playlist</th><th>Visibility</th><th>Videos</th><th>Created</th></tr></thead>
          <tbody>{data.items.map((p) => (
            <tr key={p.id}><td><a className="linkbtn" href={p.url} target="_blank" rel="noreferrer">{p.title}</a></td><td><Badge variant="neutral" label={p.privacy || "-"} /></td><td>{p.videos}</td><td>{longDate(p.created)}</td></tr>
          ))}</tbody></table></div>
      )}
    </section>
  )
}
