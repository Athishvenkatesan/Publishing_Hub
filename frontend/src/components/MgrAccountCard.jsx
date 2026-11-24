// One account on the manager screen (YouTube or LinkedIn): what it is, whether it is signed in, and what you can do with it.
import { useState } from "react"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"
import { Link } from "react-router"
import { KINDS } from "../lib/mgrKinds.js"
import { popupFailure } from "../lib/liPopup.js"
import MgrChecklist from "./MgrChecklist.jsx"
import MgrEditPanel from "./MgrEditPanel.jsx"
import MgrExpiry from "./MgrExpiry.jsx"
import MgrTokenBox from "./MgrTokenBox.jsx"

export default function MgrAccountCard({ acct, accounts, onChanged, onReuse, openCheck, checkKey = 0, kind = "youtube" }) {
  const k = KINDS[kind]
  const [open, setOpen] = useState(openCheck)
  const [editing, setEditing] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState("")
  const [err, setErr] = useState("")
  const [tick, setTick] = useState(0)
  const [tokenOpen, setTokenOpen] = useState(false)
  const mine = acct.source === "file"
  const editable = mine || kind === "youtube"  // YouTube accounts set in .env are edited there by the backend
  const reusedBy = accounts.filter((a) => a.client_from === acct.key).length

  // Re-reads this account's sign-in and runs the checklist again, opening it so the answer is in view.
  const checkAgain = () => run("check", async () => { await onChanged(); setOpen(true); setTick((t) => t + 1) })
  async function run(label, fn) {
    setBusy(label); setErr("")
    try { await fn() } catch (e) { setErr(e.message) } finally { setBusy("") }
  }
  const connect = (opts = {}) => run("connect", async () => {
    if (k.popup) {  // sign in in a popup; afterwards refresh the card and its checklist either way
      const r = await k.popup(acct.key)
      onChanged(); setOpen(true); setTick((t) => t + 1)
      if (!r.ok) throw new Error(popupFailure(r))
      return
    }
    try { window.location.href = (await k.connect(acct.key, opts)).url } catch (e) { setOpen(true); setTick((t) => t + 1); throw e }  // show the checklist beside the reason
  })
  const disconnect = () => run("disconnect", async () => { await k.disconnect(acct.key); onChanged(); setTick((t) => t + 1) })
  const fields = [
    { name: "label", label: "Account name or email", type: "text" },
    ...(acct.client_from ? [] : [
      { name: "client_id", label: "Client ID", type: "text", placeholder: k.idPlaceholder },
      { name: "client_secret", label: "Client secret", type: "secret", placeholder: k.secretPlaceholder, help: "Press Show to see the saved secret. Paste a new one to replace it." }]),
    { name: "expires_on", label: "Expiry date", type: "date", help: `Your own reminder, for example when the ${k.appWord}'s secret or this access runs out. Clear it to remove.` },
  ]
  const save = async (diff) => { await k.edit(acct.key, diff); setEditing(false); onChanged(); setTick((t) => t + 1) }
  const remove = () => run("remove", async () => { await k.remove(acct.key); onChanged() })

  return (
    <article className="panel acct-card">
      <div className="panel-head">
        <div>
          <Text weight="semibold">{acct.label}</Text>
          <div className="badges">
            <Badge variant={acct.connected ? "success" : acct.expired ? "warning" : "neutral"} label={acct.connected ? "Connected" : acct.expired ? "Sign-in ran out" : "Not connected"} />
            <Badge variant="neutral" label={mine ? "Added here" : "From .env"} />
            {acct.client_from && <Badge variant="info" label={`Shares a ${k.appWord}`} />}
            {!acct.configured && <Badge variant="warning" label="Needs client ID and secret" />}
          </div>
          {acct.name && <Text size="sm">{acct.name}{acct.email ? ` - ${acct.email}` : ""}</Text>}
          <MgrExpiry signinAt={acct.signin_expires_at} signinNote={acct.signin_note} expiresOn={acct.expires_on} />
          <Text size="sm" color="secondary">{acct.client_from ? `${k.appWord} of ${accounts.find((a) => a.key === acct.client_from)?.label || acct.client_from}` : acct.client_hint ? `${k.appWord} ${acct.client_hint}` : `No ${k.appWord} yet`}</Text>
        </div>
      </div>
      {err && <Banner status="error" title="Could not complete" description={err} isDismissable onDismiss={() => setErr("")} />}
      <div className="row-btns">
        {acct.configured && !acct.connected && <Button label="Connect" isLoading={busy === "connect"} onClick={() => connect()} />}
        {acct.connected && <Button variant="secondary" label="Disconnect" isLoading={busy === "disconnect"} onClick={disconnect} />}
        <Button variant="secondary" label={open ? "Hide checklist" : "Check setup"} onClick={() => setOpen(!open)} />
        <Button variant="secondary" label="Check again" isLoading={busy === "check"} onClick={checkAgain} />
        {acct.configured && k.token && <Button variant="secondary" label={tokenOpen ? "Hide token box" : acct.connected ? "Replace the token" : "Connect with a token"} onClick={() => setTokenOpen(!tokenOpen)} />}
        {acct.configured && <Button variant="secondary" label={`Another ${k.unit}, same ${k.appWord}`} onClick={() => onReuse(acct.key)} />}
        {acct.connected && k.studio && <Link className="btn-link btn-link--ghost" to={k.studio(acct.key)}>Open Studio</Link>}
      </div>
      {editable && (
        <div className="row-btns">
          <Button size="sm" variant="secondary" label="Edit" onClick={() => setEditing(true)} />
          {mine && (confirm
            ? <><Button size="sm" label="Yes, remove" isLoading={busy === "remove"} onClick={remove} /><Button size="sm" variant="secondary" label="Keep it" onClick={() => setConfirm(false)} /></>
            : <Button size="sm" variant="secondary" label="Remove" onClick={() => setConfirm(true)} />)}
        </div>
      )}
      {confirm && <Text size="sm" color="secondary">{k.removeNote}{reusedBy ? ` ${reusedBy} other account(s) share this ${k.appWord}, so remove those first.` : ""}</Text>}
      {!mine && <Text size="sm" color="secondary">Set in backend/.env ({acct.env_names || "see .env.example"}). Edit saves your changes there; to remove it, edit that file.</Text>}
      {tokenOpen && <MgrTokenBox kind={kind} acct={acct} onSaved={() => { setTokenOpen(false); setOpen(true); onChanged(); setTick((t) => t + 1) }} />}
      {open && <MgrChecklist acct={acct} onConnect={connect} refreshKey={`${tick}:${checkKey}`} kind={kind} />}
      <MgrEditPanel open={editing} title={`Edit ${acct.label}`} sub={acct.client_from ? `${k.name} account. It shares another account's ${k.appWord}: change the client ID and secret on that account.` : `${k.name} account. These are the saved values; only what you change is saved.`} fields={fields}
        load={() => k.values(acct.key)} onSave={save} onClose={() => setEditing(false)} />
    </article>
  )
}
