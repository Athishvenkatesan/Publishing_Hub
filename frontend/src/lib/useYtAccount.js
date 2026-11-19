// Which YouTube account a screen works on: ?account= in the address, else the remembered one, else the first.
import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router"
import { setYtAccount, ytAccounts } from "./api.js"

export function useYtAccount() {
  const [params] = useSearchParams()
  const [accounts, setAccounts] = useState([])
  const [account, setAccount] = useState("")
  const [error, setError] = useState("")
  const pick = useCallback((key) => {
    setYtAccount(key); setAccount(key)
    try { localStorage.setItem("ytAccount", key) } catch { /* no storage: the choice is just not remembered */ }
  }, [])
  const reload = useCallback(() => ytAccounts().then((d) => { setAccounts(d.accounts); return d }).catch((e) => { setError(e.message); return null }), [])
  useEffect(() => {
    reload().then((d) => {
      if (!d) return
      let saved = ""
      try { saved = localStorage.getItem("ytAccount") || "" } catch { /* no storage */ }
      pick([params.get("account"), saved, d.default].find((k) => k && d.accounts.some((a) => a.key === k)) || d.default)
    })
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  return { accounts, account, pick, reload, error, ready: !!account }
}
