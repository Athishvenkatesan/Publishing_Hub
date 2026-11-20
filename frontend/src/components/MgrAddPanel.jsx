// Slide-in panel: add a YouTube account with its Google client ID and secret, or another channel on a Google app you already added.
import { useEffect, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Heading } from "@astryxdesign/core/Heading"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Text } from "@astryxdesign/core/Text"
import { TextInput } from "@astryxdesign/core/TextInput"
import { mgrAdd } from "../lib/api.js"
import MgrSetupNotes from "./MgrSetupNotes.jsx"

export default function MgrAddPanel({ open, preset, accounts, origin, redirectUri, onClose, onAdded }) {
  const ready = accounts.filter((a) => a.configured)
  const [mode, setMode] = useState("new")
  const [label, setLabel] = useState("")
  const [clientId, setClientId] = useState("")
  const [secret, setSecret] = useState("")
  const [from, setFrom] = useState("")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  useEffect(() => {  // each time it opens: start clean, or preset to "another channel on this Google app"
    if (!open) return
    setErr(""); setLabel(""); setClientId(""); setSecret("")
    setMode(preset ? "reuse" : "new"); setFrom(preset || ready[0]?.key || "")
  }, [open, preset])  // eslint-disable-line react-hooks/exhaustive-deps

  async function save() {
    setBusy(true); setErr("")
    try {
      const body = mode === "reuse" ? { label, client_from: from } : { label, client_id: clientId, client_secret: secret }
      onAdded(await mgrAdd(body)); setSecret("")
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const canSave = label.trim() && (mode === "reuse" ? from : clientId.trim() && secret.trim())

  return (
    <>
      <div className={`scrim${open ? " scrim--on" : ""}`} onClick={onClose} />
      <aside className={`drawer${open ? " drawer--on" : ""}`} aria-hidden={!open}>
        <header className="drawer-head">
          <div><Heading level={3}>Add a YouTube account</Heading>
            <Text size="sm" color="secondary">Each account is one channel, signed in with its own Google login.</Text></div>
          <Button variant="secondary" size="sm" label="Close" onClick={onClose} />
        </header>
        {err && <Banner status="error" title="Could not add the account" description={err} />}
        {ready.length > 0 && (
          <SegmentedControl label="Which Google app?" value={mode} onChange={setMode}>
            <SegmentedControlItem value="new" label="A new Google app" />
            <SegmentedControlItem value="reuse" label="One I already added" />
          </SegmentedControl>
        )}
        <TextInput label="Account name or email" isRequired value={label} onChange={setLabel} placeholder="channel-owner@gmail.com" />
        {mode === "new" ? (
          <>
            <TextInput label="Client ID" isRequired value={clientId} onChange={setClientId} placeholder="123456789-abc.apps.googleusercontent.com" />
            <label className="sel-wrap"><span className="fp-label">Client secret</span>
              <input className="sel" type="password" autoComplete="off" value={secret} onChange={(e) => setSecret(e.target.value)} placeholder="GOCSPX-..." /></label>
            <Text size="sm" color="secondary">The secret is saved on this computer only. It is never shown again, and it never goes to GitHub.</Text>
            <MgrSetupNotes origin={origin} redirectUri={redirectUri} email={label.trim()} />
          </>
        ) : (
          <>
            <label className="sel-wrap"><span className="fp-label">Use the Google app of</span>
              <select className="sel" value={from} onChange={(e) => setFrom(e.target.value)}>{ready.map((a) => <option key={a.key} value={a.key}>{a.label}</option>)}</select></label>
            <Text size="sm" color="secondary">Use this for a second channel, or a second Google login, on the same Google app. You sign in separately for each. All of them share that Google project's limits.</Text>
          </>
        )}
        <Button label="Add account" isLoading={busy} isDisabled={!canSave || busy} onClick={save} />
      </aside>
    </>
  )
}
