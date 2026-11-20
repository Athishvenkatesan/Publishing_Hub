// Step 1 on the YouTube screen: how many accounts and channels are set up. Choosing where a video goes happens in "Post to".
import { Link } from "react-router"
import { Banner } from "@astryxdesign/core/Banner"
import { Text } from "@astryxdesign/core/Text"

export default function YtOverview({ accounts, profiles, notice, loading, account }) {
  const signedIn = accounts.filter((a) => a.connected).length
  const channels = Object.keys(profiles).length || signedIn
  const waiting = accounts.length - signedIn
  return (
    <div className="stack">
      {notice && <Banner status={notice.status} title={notice.title} description={notice.description} />}
      <div className="counts">
        <div className="count"><b>{loading && !accounts.length ? "-" : accounts.length}</b><Text size="sm" color="secondary">{accounts.length === 1 ? "Account" : "Accounts"}</Text></div>
        <div className="count"><b>{loading && !accounts.length ? "-" : channels}</b><Text size="sm" color="secondary">{channels === 1 ? "Channel" : "Channels"}</Text></div>
      </div>
      {waiting > 0 && <Text size="sm" color="secondary">{waiting} {waiting === 1 ? "account is" : "accounts are"} not signed in. Press Connect next to {waiting === 1 ? "it" : "them"} in the Post to list below.</Text>}
      {!accounts.length && !loading && <Text size="sm" color="secondary">No accounts yet. Add one to start.</Text>}
      <div className="btn-pair">
        <Link className="btn-link btn-link--ghost" to="/youtube/accounts">Manage accounts</Link>
        {signedIn > 0 && <Link className="btn-link" to={`/youtube/studio${account ? "?account=" + account : ""}`}>Studio management</Link>}
      </div>
    </div>
  )
}
