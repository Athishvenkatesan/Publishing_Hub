// One account on the manager screen (YouTube or LinkedIn): what it is, whether it is signed in, and what you can do with it.
import { useState } from "react"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"
import { TextInput } from "@astryxdesign/core/TextInput"
import { Link } from "react-router"
import { KINDS } from "../lib/mgrKinds.js"
import { popupFailure } from "../lib/liPopup.js"
import MgrChecklist from "./MgrChecklist.jsx"
import MgrTokenBox from "./MgrTokenBox.jsx"

export default function MgrAccountCard({ acct, accounts, onChanged, onReuse, openCheck, kind = "youtube" }) {
  const k = KINDS[kind]
  const [open, setOpen] = useState(openCheck)
  const [renaming, setRenaming] = useState(false)
  const [name, setName] = useState(acct.label)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState("")
  const [err, setErr] = useState("")
  const [tick, setTick] = useState(0)
  const [tokenOpen, setTokenOpen] = useState(false)
  const mine = acct.source === "file"
  const reusedBy = accounts.filter((a) => a.client_from === acct.key).length

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
  const rename = () => run("rename", async () => { await k.edit(acct.key, { label: name }); setRenaming(false); onChanged() })
  const remove = () => run("remove", async () => { await k.remove(acct.key); onChanged() })

  return (
    <article className="panel acct-card">
      <div className="panel-head">
        <div>
          {renaming ? <TextInput label="Account name" value={name} onChange={setName} /> : <Text weight="semibold">{acct.label}</Text>}
          <div className="badges">
            <Badge variant={acct.connected ? "success" : acct.expired ? "warning" : "neutral"} label={acct.connected ? "Connected" : acct.expired ? "Sign-in ran out" : "Not connected"} />
            <Badge variant="neutral" label={mine ? "Added here" : "From .env"} />
            {acct.client_from && <Badge variant="info" label={`Shares a ${k.appWord}`} />}
            {!acct.configured && <Badge variant="warning" label="Needs client ID and secret" />}
          </div>
          {acct.name && <Text size="sm">{acct.name}{acct.email ? ` - ${acct.email}` : ""}</Text>}
          <Text size="sm" color="secondary">{acct.client_from ? `${k.appWord} of ${accounts.find((a) => a.key === acct.client_from)?.label || acct.client_from}` : acct.client_hint ? `${k.appWord} ${acct.client_hint}` : `No ${k.appWord} yet`}</Text>
        </div>
      </div>
      {err && <Banner status="error" title="Could not complete" description={err} isDismissable onDismiss={() => setErr("")} />}
      <div className="row-btns">
        {acct.configured && !acct.connected && <Button label="Connect" isLoading={busy === "connect"} onClick={() => connect()} />}
        {acct.connected && <Button variant="secondary" label="Disconnect" isLoading={busy === "disconnect"} onClick={disconnect} />}
        <Button variant="secondary" label={open ? "Hide checklist" : "Check setup"} onClick={() => setOpen(!open)} />
        {acct.configured && k.token && <Button variant="secondary" label={tokenOpen ? "Hide token box" : acct.connected ? "Replace the token" : "Connect with a token"} onClick={() => setTokenOpen(!tokenOpen)} />}
        {acct.configured && <Button variant="secondary" label={`Another ${k.unit}, same ${k.appWord}`} onClick={() => onReuse(acct.key)} />}
        {acct.connected && k.studio && <Link className="btn-link btn-link--ghost" to={k.studio(acct.key)}>Open Studio</Link>}
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
      {confirm && <Text size="sm" color="secondary">{k.removeNote}{reusedBy ? ` ${reusedBy} other account(s) share this ${k.appWord}, so remove those first.` : ""}</Text>}
      {!mine && <Text size="sm" color="secondary">Set in backend/.env ({acct.env_names || "see .env.example"}). Edit that file to change or remove it.</Text>}
      {tokenOpen && <MgrTokenBox kind={kind} acct={acct} onSaved={() => { setTokenOpen(false); setOpen(true); onChanged(); setTick((t) => t + 1) }} />}
      {open && <MgrChecklist acct={acct} onConnect={connect} refreshKey={tick} kind={kind} />}
    </article>
  )
}
