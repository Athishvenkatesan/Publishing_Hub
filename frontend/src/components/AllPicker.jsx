// "Post to" for one platform on the combined screen: a switch for the platform plus its account picker.
import { useNavigate } from "react-router"
import { Text } from "@astryxdesign/core/Text"
import YtChannelPicker from "./YtChannelPicker.jsx"

export default function AllPicker({ p, accounts, profiles, enabled, onToggle, value, onChange }) {
  const navigate = useNavigate()
  const any = accounts.some((a) => a.connected)
  return (
    <div className="stack">
      <label className="chk">
        <input type="checkbox" checked={enabled} disabled={!any} onChange={(e) => onToggle(e.target.checked)} />
        <span className="dd-text"><b>{p.name}</b><Text size="sm" color="secondary">{any ? p.note : `Connect ${p.name} first.`}</Text></span>
      </label>
      {enabled && (
        <YtChannelPicker accounts={accounts} profiles={profiles} value={value} onChange={onChange} noun={p.unit.toLowerCase() === "channel" ? "channel" : "account"} manageTo={p.accountsRoute}
          onAdd={() => navigate(p.accountsRoute)} onConnect={(key) => navigate(`${p.accountsRoute}?account=${key}`)} />
      )}
    </div>
  )
}
