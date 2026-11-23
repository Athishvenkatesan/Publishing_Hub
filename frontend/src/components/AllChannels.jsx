// Step 1 on the combined screen: for each platform, how many accounts are set up and signed in, and the button to manage them.
import { Link } from "react-router"
import { Text } from "@astryxdesign/core/Text"

export default function AllChannels({ data, loading }) {
  return (
    <div className="counts counts--4">
      {data.map(({ p, accounts }) => {
        const signedIn = accounts.filter((a) => a.connected).length
        const waiting = accounts.length - signedIn
        return (
          <div key={p.kind} className="count stack">
            <Text weight="semibold">{p.name}{p.soon ? " (coming soon)" : ""}</Text>
            <b>{loading && !accounts.length ? "-" : accounts.length}</b>
            <Text size="sm" color="secondary">{accounts.length === 1 ? p.unit : `${p.unit}s`}, {signedIn} signed in{waiting > 0 ? `, ${waiting} not signed in` : ""}</Text>
            <Link className="btn-link btn-link--ghost" to={p.accountsRoute}>{p.kind === "meta" ? "Open the Meta screen" : "Manage accounts"}</Link>
          </div>
        )
      })}
    </div>
  )
}
