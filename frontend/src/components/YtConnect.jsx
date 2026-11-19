// Connect or disconnect the YouTube channel (Google sign-in happens on Google's own page).
import { useState } from "react"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { Link } from "react-router"
import { ytConnect, ytDisconnect } from "../lib/api.js"

export default function YtConnect({ status, loading, notice, reload }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  async function connect() {
    setBusy(true); setErr("")
    try { window.location.href = (await ytConnect()).url } catch (e) { setErr(e.message); setBusy(false) }
  }
  async function disconnect() {
    setBusy(true); await ytDisconnect().catch(() => {}); setBusy(false); reload()
  }

  if (loading) return <div className="working"><Spinner /><Text size="sm">Checking YouTube...</Text></div>
  const ch = status?.channel
  return (
    <div className="stack">
      {notice && <Banner status={notice.status} title={notice.title} description={notice.description} />}
      {err && <Banner status="error" title="Could not start sign-in" description={err} />}
      {status && !status.configured && <Banner status="warning" title="Google app not set"
        description="This account has no Google client yet. Put its client ID and secret in backend/.env (see .env.example) and restart the backend." />}
      {status?.error && <Banner status="error" title="YouTube problem" description={status.error} />}
      {status?.setup_problem && <Banner status="warning" title="Google setup is not finished" description={status.setup_problem} />}
      {ch ? (
        <div className="acc">
          <span className="dot dot--youtube">Y</span>
          <div className="acc-main"><Text weight="semibold">{ch.title}</Text>
            <Text size="sm" color="secondary">{ch.handle}{ch.subscribers != null ? ` - ${ch.subscribers} subscribers` : ""}</Text></div>
          <Badge variant="success" label="Connected" />
        </div>
      ) : status?.connected && !status.error ? <Text size="sm">Signed in, but no channel was found on this Google account.</Text>
        : <Text size="sm" color="secondary">Not connected. Press Connect YouTube, sign in with the Google account that owns the channel, and allow upload access.</Text>}
      <div className="row-btns">
        {status?.configured && !status.connected && <Button label={status.label ? `Connect ${status.label}` : "Connect YouTube"} isLoading={busy} isDisabled={!!status.setup_problem} onClick={connect} />}
        {status?.setup_problem && <Button variant="secondary" label="Check again" onClick={reload} />}
        {status?.connected && <Link className="btn-link" to={`/youtube/studio${status.account ? "?account=" + status.account : ""}`}>Studio management</Link>}
        {status?.connected && <Button variant="secondary" label="Disconnect" isLoading={busy} onClick={disconnect} />}
      </div>
      {status?.configured && !status.connected && (
        <details>
          <summary><Text size="sm" color="secondary">Google blocked the sign-in?</Text></summary>
          <ul className="help">
            <li><b>Error 403 org_internal:</b> the Google app is set to Internal. In Google Cloud open Google Auth Platform, Audience, and switch the user type to External, then add your Google account under Test users.</li>
            <li><b>Access blocked / not a test user:</b> add your Google account under Audience, Test users.</li>
            <li><b>redirect_uri_mismatch:</b> use a Desktop app OAuth client, or add the redirect address shown below to a Web client.</li>
            <li><b>App not verified:</b> press Advanced, then Go to the app. This is normal for your own test app.</li>
          </ul>
        </details>
      )}
      {status?.configured && (
        <Text size="sm" color="secondary">Google redirect address (must be listed in your Google OAuth client): <span className="mono">{status.redirect_uri}</span></Text>
      )}
    </div>
  )
}
