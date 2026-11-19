// One account on the manager screen: what it is, whether it is signed in, and what you can do with it.
import { useState } from "react"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"
import { TextInput } from "@astryxdesign/core/TextInput"
import { Link } from "react-router"
import { ytDisconnect, setYtAccount, mgrDelete, mgrEdit, connectAccount_ } from "../lib/api.js"
import MgrChecklist from "./MgrChecklist.jsx"

export default function MgrAccountCard({ acct, accounts, onChanged, onReuse, openCheck }) {
  const [open, setOpen] = useState(openCheck)
  const [renaming, setRenaming] = useState(false)
  const [name, setName] = useState(acct.label)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState("")
  const [err, setErr] = useState("")
  const [tick, setTick] = useState(0)
  const mine = acct.source === "file"
  const reusedBy = accounts.filter((a) => a.client_from === acct.key).length

  async function run(label, fn) {
    setBusy(label); setErr("")
    try { await fn() } catch (e) { setErr(e.message) } finally { setBusy("") }
  }
  const connect = (opts = {}) => run("connect", async () => {
    try { window.location.href = (await connectAccount_(acct.key, opts, "accounts")).url } catch (e) { setOpen(true); setTick((t) => t + 1); throw e }  // show the checklist beside the reason
  })
  const disconnect = () => run("disconnect", async () => { setYtAccount(acct.key); await ytDisconnect(); onChanged(); setTick((t) => t + 1) })
  const rename = () => run("rename", async () => { await mgrEdit(acct.key, { label: name }); setRenaming(false); onChanged() })
  const remove = () => run("remove", async () => { await mgrDelete(acct.key); onChanged() })

  return (
    <article className="panel acct-card">
      <div className="panel-head">
        <div>
          {renaming ? <TextInput label="Account name" value={name} onChange={setName} /> : <Text weight="semibold">{acct.label}</Text>}
          <div className="badges">
            <Badge variant={acct.connected ? "success" : "neutral"} label={acct.connected ? "Connected" : "Not connected"} />
            <Badge variant="neutral" label={mine ? "Added here" : "From .env"} />
            {acct.client_from && <Badge variant="info" label="Shares a Google app" />}
            {!acct.configured && <Badge variant="warning" label="Needs client ID and secret" />}
          </div>
          <Text size="sm" color="secondary">{acct.client_from ? `Google app of ${accounts.find((a) => a.key === acct.client_from)?.label || acct.client_from}` : acct.client_hint ? `Google app ${acct.client_hint}` : "No Google app yet"}</Text>
        </div>
      </div>
      {err && <Banner status="error" title="Could not complete" description={err} isDismissable onDismiss={() => setErr("")} />}
      <div className="row-btns">
        {acct.configured && !acct.connected && <Button label="Connect" isLoading={busy === "connect"} onClick={() => connect()} />}
        {acct.connected && <Button variant="secondary" label="Disconnect" isLoading={busy === "disconnect"} onClick={disconnect} />}
        <Button variant="secondary" label={open ? "Hide checklist" : "Check setup"} onClick={() => setOpen(!open)} />
        {acct.configured && <Button variant="secondary" label="Another channel, same Google app" onClick={() => onReuse(acct.key)} />}
        {acct.connected && <Link className="btn-link btn-link--ghost" to={`/youtube/studio?account=${acct.key}`}>Open Studio</Link>}
      </div>
      {mine && (
        <div className="row-btns">
          {renaming ? <><Button size="sm" label="Save name" isLoading={busy === "rename"} onClick={rename} /><Button size="sm" variant="secondary" label="Cancel" onClick={() => setRenaming(false)} /></>
            : <Button size="sm" variant="secondary" label="Rename" onClick={() => setRenaming(true)} />}
          {confirm
            ? <><Button size="sm" label="Yes, remove" isLoading={busy === "remove"} onClick={remove} /><Button size="sm" variant="secondary" label="Keep it" onClick={() => setConfirm(false)} /></>
            : <Button size="sm" variant="secondary" label="Remove" onClick={() => setConfirm(true)} />}
        </div>
      )}
      {confirm && <Text size="sm" color="secondary">This removes the saved Google app and sign-in from this computer{reusedBy ? ` (${reusedBy} other channel(s) share it, so remove those first)` : ""}. Videos already on YouTube are not touched.</Text>}
      {!mine && <Text size="sm" color="secondary">Set in backend/.env ({acct.env_names || "see .env.example"}). Edit that file to change or remove it.</Text>}
      {open && <MgrChecklist acct={acct} onConnect={connect} refreshKey={tick} />}
    </article>
  )
}
