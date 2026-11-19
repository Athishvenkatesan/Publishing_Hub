// Load something when a page opens or its inputs change. Keeps the previous data on screen while it reloads.
import { useCallback, useEffect, useState } from "react"

export function useLoad(fn, deps) {
  const [s, setS] = useState({ data: null, error: "", loading: true })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(() => {
    setS((p) => ({ ...p, loading: true, error: "" }))
    return fn().then((data) => setS({ data, error: "", loading: false })).catch((e) => setS((p) => ({ ...p, error: e.message, loading: false })))
  }, deps)
  useEffect(() => { run() }, [run])
  return { ...s, reload: run }
}
