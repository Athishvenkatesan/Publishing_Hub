// Sign an account in with a token made in the vendor's own portal, for when no redirect URL is set up. Used by the LinkedIn cards.
import { useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"
import { KINDS } from "../lib/mgrKinds.js"

export default function MgrTokenBox({ kind, acct, onSaved }) {
  const k = KINDS[kind]
  const [token, setToken] = useState("")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  async function save() {
    setBusy(true); setErr("")
    try { await k.token(acct.key, token); setToken(""); onSaved() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="token-box">
      <Text size="sm" weight="semibold">Connect with a token (no redirect URL needed)</Text>
      <ol className="guide">{k.tokenSteps.map((s) => <li key={s}><Text size="sm">{s}</Text></li>)}</ol>
      <a className="linkbtn" href={k.tokenLink.url} target="_blank" rel="noreferrer">{k.tokenLink.label}</a>
      {err && <Banner status="error" title="Could not use that token" description={err} />}
      <label className="sel-wrap"><span className="fp-label">Access token</span>
        <input className="sel" type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} placeholder="AQ..." /></label>
      <div><Button label="Save token" isLoading={busy} isDisabled={!token.trim() || busy} onClick={save} /></div>
      <Text size="sm" color="secondary">The token stays on this computer only. It works for about 60 days, then make a new one the same way.</Text>
    </div>
  )
}
