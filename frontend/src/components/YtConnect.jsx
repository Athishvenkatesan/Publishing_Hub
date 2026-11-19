// Connect or disconnect the YouTube channel (Google sign-in happens on Google's own page).
import { useState } from "react"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
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
        description="Put YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in backend/.env and restart the backend." />}
      {status?.error && <Banner status="error" title="YouTube problem" description={status.error} />}
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
        {status?.configured && !status.connected && <Button label="Connect YouTube" isLoading={busy} onClick={connect} />}
        {status?.connected && <Button variant="secondary" label="Disconnect" isLoading={busy} onClick={disconnect} />}
      </div>
      {status?.configured && (
        <Text size="sm" color="secondary">Google redirect address (must be listed in your Google OAuth client): <span className="mono">{status.redirect_uri}</span></Text>
      )}
    </div>
  )
}
