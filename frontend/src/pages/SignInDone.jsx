// Where a sign-in popup (LinkedIn or X) lands: tell the app page the result, then close the popup.
import { useEffect } from "react"
import { Link, useSearchParams } from "react-router"
import { Text } from "@astryxdesign/core/Text"

export default function SignInDone({ type = "linkedin-signin", back = "/linkedin/accounts", name = "LinkedIn" }) {
  const [params] = useSearchParams()
  const ok = params.get("connected") === "1", error = params.get("error") || ""
  useEffect(() => {
    if (!window.opener) return
    window.opener.postMessage({ type, ok, error, account: params.get("account") || "" }, window.location.origin)
    window.close()
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="page stack">
      <Text weight="semibold">{ok ? `${name} connected.` : `${name} sign-in did not finish.`}</Text>
      {error && <Text size="sm">{error}</Text>}
      <Text size="sm" color="secondary">You can close this window. <Link to={back}>Back to the accounts</Link></Text>
    </div>
  )
}
