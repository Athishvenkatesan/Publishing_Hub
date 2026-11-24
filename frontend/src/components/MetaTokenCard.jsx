// The Meta card's body: the Facebook + Instagram token (who it is, when it runs out, what it reaches) and the buttons to edit it or make it last 60 days.
// The three App IDs (Facebook, Instagram, Threads) are shown and edited here too.
import { useState } from "react"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"
import { metaMgrEdit, metaMgrExtend, metaMgrRemove, metaMgrValues } from "../lib/api.js"
import MgrEditPanel from "./MgrEditPanel.jsx"
import MgrExpiry from "./MgrExpiry.jsx"

const CAN = { facebook_video: "Facebook", instagram_video: "Instagram", threads_video: "Threads" }

function fieldsFor(t) {
  const meta = t.key === "meta"
  return [
    { name: "token", label: meta ? "Facebook + Instagram access token" : "Threads access token", type: "secret", placeholder: "Paste the token",
      help: meta ? "From the Graph API Explorer. Press Show to see the saved one; paste a new one to replace it, or clear it to remove." : "From the Threads tester tool. Paste a new one to replace it, or clear it to remove." },
    ...(meta ? [
      { name: "app_id", label: "Facebook App ID", type: "text", placeholder: "1145493691227848", help: "App settings, Basic." },
      { name: "instagram_app_id", label: "Instagram App ID", type: "text", placeholder: "1234567890123456", help: "Instagram use case, API setup. Digits only." },
      { name: "threads_app_id", label: "Threads App ID", type: "text", placeholder: "1234567890123456", help: "Threads use case, Settings. Digits only." }] : []),
    { name: "app_secret", label: meta ? "App secret" : "Threads app secret", type: "secret", placeholder: "Paste the secret",
      help: meta ? "App settings, Basic. With it, every token you paste is swapped for a 60-day one." : "Use cases, Threads, Settings. With it, the Threads token lasts 60 days." },
    { name: "expires_on", label: "Expiry date", type: "date", help: "Your own reminder date. Clear it to remove." },
  ]
}

export default function MetaTokenCard({ t, onChanged }) {
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")
  const [ok, setOk] = useState("")
  const short = t.expires_at && t.expires_at - Date.now() / 1000 < 2 * 86400  // under two days: a short token
  const status = !t.has_token ? ["neutral", "No token"] : t.valid ? ["success", "Working"] : ["error", "Not working"]

  async function extend() {
    setBusy(true); setErr(""); setOk("")
    try { await metaMgrExtend(t.key); setOk("Swapped for a 60-day token."); onChanged() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const [confirm, setConfirm] = useState(false)
  async function remove() {
    setBusy(true); setErr(""); setOk("")
    try { await metaMgrRemove(); setConfirm(false); setOk("Removed. Add a new token with Add the token."); onChanged() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  async function save(diff) {
    await metaMgrEdit(t.key, diff); setEditing(false); setOk("Saved."); onChanged()
  }

  return (
    <section className="tok-section">
      <div className="stack stack--tight">
        <div className="badges">
          <Badge variant={status[0]} label={status[1]} />
          {t.has_token && <Badge variant="neutral" label={`Token ${t.token_hint}`} />}
          {t.has_app_secret ? <Badge variant="info" label="App secret saved" /> : <Badge variant="neutral" label="No app secret" />}
        </div>
        {t.who && <Text size="sm">{t.who}</Text>}
        <div className="app-ids">
          {[["Facebook App ID", t.app_id], ["Instagram App ID", t.instagram_app_id], ["Threads App ID", t.threads_app_id]].map(([name, id]) => (
            <Text key={name} size="sm"><strong>{name}</strong>{" "}{id ? <code>{id}</code> : <span className="muted">Not set. Add it with Edit.</span>}</Text>))}
        </div>
        {t.error && <Text size="sm" color="secondary">{t.error}</Text>}
        <MgrExpiry what="Token expires" signinAt={t.expires_at} never={t.never_expires}
          signinNote={!t.has_token ? "No token yet." : !t.valid ? "Expired or not working. Paste a new token with Edit."
            : "Not known. A token from the tester tool lasts about 1 hour; add the app secret to make it last 60 days."} expiresOn={t.expires_on} />
        {t.pages?.map((p) => <Text key={p.name} size="sm" color="secondary">Page {p.name}{p.instagram ? ` - Instagram @${p.instagram}` : " - no Instagram linked"}</Text>)}
        {t.can && Object.keys(t.can).length > 0 && (
          <div className="tok-scopes">{Object.entries(CAN).map(([k, n]) => k in t.can && <Badge key={k} variant={t.can[k] ? "success" : "neutral"} label={`${n}: ${t.can[k] ? "can post" : "cannot yet"}`} />)}</div>
        )}
      </div>
      {err && <Banner status="error" title="Could not complete" description={err} isDismissable onDismiss={() => setErr("")} />}
      {ok && <Banner status="success" title={ok} isDismissable onDismiss={() => setOk("")} />}
      <div className="row-btns">
        <Button label={t.has_token ? "Edit" : "Add the token"} onClick={() => setEditing(true)} />
        {t.has_token && t.has_app_secret && short && <Button variant="secondary" label="Make it last 60 days" isLoading={busy} onClick={extend} />}
        {(t.has_token || t.app_id || t.has_app_secret) && (confirm
          ? <><Button label="Yes, remove" isLoading={busy} onClick={remove} /><Button variant="secondary" label="Keep it" onClick={() => setConfirm(false)} /></>
          : <Button variant="secondary" label="Remove" onClick={() => setConfirm(true)} />)}
      </div>
      {confirm && <Text size="sm" color="secondary">This clears the Meta token, the three App IDs and the app secret from backend/.env on this computer. Posts already on Facebook, Instagram or Threads are not touched. You cannot undo it here.</Text>}
      {t.has_token && !t.has_app_secret && short && <Text size="sm" color="secondary">This token runs out soon. Add the app secret with Edit and it is swapped for a 60-day one.</Text>}
      {t.scopes?.length > 0 && <details><summary><Text size="sm" color="secondary">Permissions ({t.scopes.length})</Text></summary><p className="mono">{t.scopes.join(", ")}</p></details>}
      <MgrEditPanel open={editing} title="Edit Meta" sub="These are the values saved in backend/.env on this computer. Only what you change is saved."
        fields={fieldsFor(t)} load={() => metaMgrValues(t.key)} onSave={save} onClose={() => setEditing(false)} />
    </section>
  )
}
