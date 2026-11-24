// Step 1 on the Meta screen: who the token belongs to, how many Pages, which platforms are ready. Full details fold open.
import { Link } from "react-router"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"
import { postable } from "../lib/meta.js"
import FbCheck from "./FbCheck.jsx"

const PLATFORMS = [["facebook_video", "Facebook"], ["instagram_video", "Instagram"], ["threads_video", "Threads"]]

export default function MetaOverview({ state, onCheck }) {
  const { loading, error, data } = state
  const caps = data?.capabilities || []
  const ready = PLATFORMS.filter(([k]) => caps.find((c) => c.key === k)?.ok)
  return (
    <div className="stack">
      {error && <Banner status="error" title="Token check failed" description={error} />}
      {data && <Text size="sm" color="secondary">Token belongs to <b>{data.user.name}</b></Text>}
      <div className="counts">
        <div className="count"><b>{loading && !data ? "-" : postable(data?.pages).length}</b><Text size="sm" color="secondary">Pages you can post to</Text></div>
        <div className="count"><b>{loading && !data ? "-" : `${ready.length} / 3`}</b><Text size="sm" color="secondary">Platforms ready</Text></div>
      </div>
      {data && <Text size="sm" color="secondary">Ready: {ready.map(([, n]) => n).join(", ") || "none"}. Not yet: {PLATFORMS.filter((p) => !ready.includes(p)).map(([, n]) => n).join(", ") || "none"}.</Text>}
      <details><summary><Text size="sm" color="secondary">Token details and what each platform needs</Text></summary>
        <FbCheck state={state} onCheck={onCheck} /></details>
      <div className="btn-pair">
        <Link className="btn-link btn-link--ghost" to="/meta/accounts">Manage accounts</Link>
        {!data && <Button variant="secondary" label="Check again" onClick={onCheck} isLoading={loading} />}
      </div>
    </div>
  )
}
