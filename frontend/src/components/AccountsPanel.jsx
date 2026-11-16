// Slide-in panel: connect and disconnect social accounts without leaving the app.
import { useState } from "react"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import { connectAccount, disconnectAccount } from "../lib/api.js"

export const NAMES = { instagram: "Instagram", youtube: "YouTube", tiktok: "TikTok", facebook: "Facebook", linkedin: "LinkedIn", twitter: "X" }

export default function AccountsPanel({ open, onClose, accounts, platforms, reload }) {
  const [busy, setBusy] = useState("")
  const [err, setErr] = useState("")
  const [confirm, setConfirm] = useState("")

  async function connect(p) {
    setBusy(p); setErr("")
    try { window.location.href = (await connectAccount(p)).url } catch (e) { setErr(e.message); setBusy("") }
  }
  async function remove(id) {
    setBusy(id); setErr("")
    try { await disconnectAccount(id); setConfirm(""); await reload() } catch (e) { setErr(e.message) }
    setBusy("")
  }

  return (
    <>
      <div className={`scrim${open ? " scrim--on" : ""}`} onClick={onClose} />
      <aside className={`drawer${open ? " drawer--on" : ""}`} aria-hidden={!open}>
        <header className="drawer-head">
          <div><Heading level={3}>Connected accounts</Heading>
            <Text size="sm" color="secondary">Add or remove channels here. No need to open Zernio.</Text></div>
          <Button variant="secondary" size="sm" label="Close" onClick={onClose} />
        </header>
        {err && <Banner status="error" title="Could not complete" description={err} isDismissable onDismiss={() => setErr("")} />}
        <div className="acc-list">
          {accounts.map((a) => (
            <div key={a.id} className="acc">
              <span className={`dot dot--${a.platform}`}>{NAMES[a.platform]?.[0]}</span>
              <div className="acc-main">
                <Text weight="semibold">@{a.username}</Text>
                <Text size="sm" color="secondary">{NAMES[a.platform] || a.platform}{a.followers != null ? ` - ${a.followers} followers` : ""}</Text>
              </div>
              <Badge variant={a.active ? "success" : "warning"} label={a.active ? "Connected" : "Reconnect"} />
              {confirm === a.id
                ? <Button size="sm" variant="secondary" label="Confirm remove" isLoading={busy === a.id} onClick={() => remove(a.id)} />
                : <Button size="sm" variant="secondary" label="Disconnect" onClick={() => setConfirm(a.id)} />}
            </div>
          ))}
          {!accounts.length && <Text color="secondary">Nothing connected yet.</Text>}
        </div>
        <Heading level={4}>Add a channel</Heading>
        <div className="add-grid">
          {platforms.map((p) => (
            <button key={p} className="add" disabled={!!busy} onClick={() => connect(p)}>
              <span className={`dot dot--${p}`}>{NAMES[p]?.[0]}</span>{busy === p ? "Opening..." : `Connect ${NAMES[p]}`}
            </button>
          ))}
        </div>
        <Text size="sm" color="secondary">You sign in on the platform's own page, then come straight back here. The free plan allows 2 accounts.</Text>
      </aside>
    </>
  )
}
