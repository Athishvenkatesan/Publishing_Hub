// What works and what still needs doing for one account (YouTube or LinkedIn). Each "to do" comes with the button that does it.
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { KINDS } from "../lib/mgrKinds.js"
import { useLoad } from "../lib/useLoad.js"

const BADGE = { ok: ["success", "Done"], todo: ["warning", "To do"], warn: ["error", "Check"] }

function Action({ action, onConnect }) {
  if (!action) return null
  if (Array.isArray(action)) return <div className="row-btns">{action.map((a) => <Action key={a.label} action={a} onConnect={onConnect} />)}</div>  // several fixes for one to-do
  if (action.kind === "link") return <a className="btn-link btn-link--ghost" href={action.url} target="_blank" rel="noreferrer">{action.label}</a>
  if (action.kind === "copy") return <Button size="sm" variant="secondary" label={action.label} onClick={() => navigator.clipboard?.writeText(action.value)} />
  if (action.kind === "connect") return <Button size="sm" label={action.label} onClick={() => onConnect(action.opts)} />
  return null
}

export default function MgrChecklist({ acct, onConnect, refreshKey, kind = "youtube" }) {
  const k = KINDS[kind]
  const { data, error, loading, reload } = useLoad(() => k.check(acct.key), [acct.key, acct.connected, refreshKey, kind])
  return (
    <div className="check">
      {loading && !data && <div className="working"><Spinner /><Text size="sm">Asking {k.asking} about this account...</Text></div>}
      {error && <Banner status="error" title="Could not check" description={error} />}
      <ul className={`check-list${loading && data ? " is-loading" : ""}`}>
        {(data?.items || []).map((i) => {
          const [variant, text] = BADGE[i.status] || BADGE.warn
          return (
            <li key={i.id}>
              <Badge variant={variant} label={text} />
              <div className="check-main"><Text weight="semibold" size="sm">{i.title}</Text>{i.detail && <Text size="sm" color="secondary">{i.detail}</Text>}</div>
              <Action action={i.action} onConnect={onConnect} />
            </li>
          )
        })}
      </ul>
      <div><Button variant="secondary" size="sm" label="Check again" isLoading={loading} onClick={reload} /></div>
    </div>
  )
}
