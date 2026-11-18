// Read-only check of the Meta token: who it is, what it may do, which Pages it reaches.
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"

export default function FbCheck({ state, onCheck }) {
  const { loading, error, data } = state
  return (
    <div className="stack">
      {loading && <div className="working"><Spinner /><Text size="sm">Asking Meta what this token can do...</Text></div>}
      {error && <Banner status="error" title="Token check failed" description={error} />}
      {data && (
        <>
          <Text size="sm" color="secondary">Token belongs to <b>{data.user.name}</b></Text>
          <div className="caps">
            {data.capabilities.map((c) => (
              <div key={c.key} className={`cap${c.ok ? " cap--ok" : ""}`}>
                <div><Badge variant={c.ok ? "success" : "neutral"} label={c.ok ? "Can do" : "Cannot yet"} /></div>
                <Text weight="semibold" size="sm">{c.label}</Text>
                <Text size="sm" color="secondary">{c.why}</Text>
              </div>
            ))}
          </div>
          <div>
            <Text size="sm" weight="semibold">Pages this token can reach</Text>
            {!data.pages.length && <Text size="sm" color="secondary">None. The token has no Page access.</Text>}
            {data.pages.map((p) => (
              <div key={p.id} className="acc">
                <span className="dot dot--facebook">F</span>
                <div className="acc-main"><Text weight="semibold">{p.name}</Text>
                  <Text size="sm" color="secondary">{p.category}{p.instagram ? ` - Instagram @${p.instagram.username}` : ""}</Text></div>
                <Badge variant={p.tasks.includes("CREATE_CONTENT") ? "success" : "warning"}
                  label={p.tasks.includes("CREATE_CONTENT") ? "Can post" : "No posting role"} />
              </div>
            ))}
          </div>
          <details><summary><Text size="sm" color="secondary">Permissions granted ({data.permissions.length})</Text></summary>
            <p className="mono">{data.permissions.join(", ") || "none"}</p></details>
        </>
      )}
      <div><Button variant="secondary" label={data ? "Check again" : "Check token"} onClick={onCheck} isLoading={loading} /></div>
    </div>
  )
}
