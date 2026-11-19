// What this app may do on the channel (read live from Google), what it cannot, and where YouTube keeps the rest.
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { connectAccount_, studioAccess } from "../lib/api.js"
import { useLoad } from "../lib/useLoad.js"

export default function StudioAccess({ account }) {
  const { data, error, loading } = useLoad(studioAccess, [account])
  const add = async (opts) => { window.location.href = (await connectAccount_(account, opts, "studio")).url }
  if (error) return <Banner status="error" title="Could not read permissions" description={error} />
  if (!data) return <div className="working"><Spinner /><Text size="sm">Reading permissions from Google...</Text></div>
  const studio = data.channel?.links?.dashboard || "https://studio.youtube.com"
  return (
    <div className={`stack${loading ? " is-loading" : ""}`}>
      <section className="panel">
        <Text weight="semibold">What this app is allowed to do</Text>
        <Text size="sm" color="secondary">Read live from Google for this account. Add a permission only if you need the feature.</Text>
        <div className="table-wrap"><table className="mini data">
          <thead><tr><th>Permission</th><th>What it allows</th><th>Status</th></tr></thead>
          <tbody>{data.scopes.map((s) => (
            <tr key={s.scope}><td><b>{s.name}</b><br /><span className="muted">{s.kind}</span></td><td>{s.allows}</td>
              <td>{s.granted ? <Badge variant="success" label="Granted" /> : <Badge variant="neutral" label="Not granted" />}</td></tr>
          ))}</tbody></table></div>
        <div className="row-btns">
          {!data.can_report && <Button label="Add the reports permission" onClick={() => add({ reports: true })} />}
          {!data.can_manage && <Button variant="secondary" label="Add the manage-videos permission" onClick={() => add({ manage: true })} />}
        </div>
        {!data.can_manage && <Text size="sm" color="secondary">Without the manage permission, the app can upload but cannot edit, change visibility, reschedule or delete a video afterwards. That permission covers your whole YouTube account, so add it only if you want those actions.</Text>}
      </section>
      <section className="panel">
        <Text weight="semibold">What YouTube does not share with apps</Text>
        <ul className="plain">
          <li><b>Who has access to the channel, and their roles.</b> Only YouTube Studio shows this. Open Settings, then Permissions.</li>
          <li><b>Revenue and ad reports.</b> They need a monetized channel and a separate permission.</li>
          <li><b>Comments.</b> Reading them needs a very broad permission that also allows deleting, so this app does not ask for it.</li>
        </ul>
        <div className="row-btns"><a className="btn-link" href={studio} target="_blank" rel="noreferrer">Open YouTube Studio</a></div>
      </section>
      <section className="panel">
        <Text weight="semibold">Roles a person can have on a channel (set in YouTube Studio)</Text>
        <div className="table-wrap"><table className="mini data"><thead><tr><th>Role</th><th>What they can do</th></tr></thead>
          <tbody>{data.roles.map((r) => <tr key={r.role}><td><b>{r.role}</b></td><td>{r.can}</td></tr>)}</tbody></table></div>
      </section>
    </div>
  )
}
