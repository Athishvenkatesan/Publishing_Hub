// Which YouTube account to work with. Each has its own Google sign-in and its own channel.
import { Link } from "react-router"
import { Text } from "@astryxdesign/core/Text"

export default function YtAccounts({ accounts, value, onChange }) {
  return (
    <div className="stack">
      <div className="panel-head"><Text size="sm" weight="semibold">YouTube account</Text><Link className="linkbtn" to="/youtube/accounts">Manage accounts</Link></div>
      {accounts.length < 2 ? null : (
      <div className="accts" role="radiogroup" aria-label="YouTube account">
        {accounts.map((a) => (
          <button type="button" key={a.key} role="radio" aria-checked={a.key === value} className={`acct${a.key === value ? " acct--on" : ""}`} onClick={() => onChange(a.key)}>
            <span className="acct-label">{a.label}</span>
            <span className="acct-state">{!a.configured ? "Setup missing" : a.connected ? "Connected" : "Not connected"}</span>
          </button>
        ))}
      </div>)}
    </div>
  )
}
