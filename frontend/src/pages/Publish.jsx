import { useCallback, useEffect, useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import AccountsPanel from "../components/AccountsPanel.jsx"
import Hero from "../components/Hero.jsx"
import Nav from "../components/Nav.jsx"
import HistoryTable from "../components/HistoryTable.jsx"
import PublishForm from "../components/PublishForm.jsx"
import { getAccounts, getHistory } from "../lib/api.js"

export default function Publish() {
  const [items, setItems] = useState([])
  const [accounts, setAccounts] = useState([])
  const [platforms, setPlatforms] = useState([])
  const [panel, setPanel] = useState(false)
  const [accErr, setAccErr] = useState("")
  const [note, setNote] = useState(() => (new URLSearchParams(window.location.search).has("connected") ? "Account connected." : ""))
  const load = useCallback(() => getHistory().then((d) => setItems(d.items)).catch(() => {}), [])
  const loadAccounts = useCallback(() => getAccounts()
    .then((d) => { setAccounts(d.accounts); setPlatforms(d.platforms); setAccErr("") })
    .catch(() => setAccErr("Cannot reach the backend, so your accounts are not loaded. Start it with: npm run dev:backend (in the POC folder). This page retries by itself.")), [])
  useEffect(() => { load(); loadAccounts(); const t = setInterval(() => { load(); loadAccounts() }, 10000); return () => clearInterval(t) }, [load, loadAccounts])
  useEffect(() => { if (note) window.history.replaceState({}, "", "/") }, [note])

  return (
    <>
      <Nav />
      <Hero items={items} accounts={accounts} onAccounts={() => setPanel(true)} />
      <div className="page stack">
        {accErr && <Banner status="error" title="Accounts not loaded" description={accErr} />}
        {note && <Banner status="success" title={note} isDismissable onDismiss={() => setNote("")} />}
        <PublishForm onDone={load} accounts={accounts} />
        <section className="history">
          <div className="history-head">
            <Heading level={3}>History</Heading>
            <Text size="sm" color="secondary">Updates every 10 seconds.</Text>
          </div>
          <HistoryTable items={items} />
        </section>
      </div>
      <AccountsPanel open={panel} onClose={() => setPanel(false)} accounts={accounts} platforms={platforms} reload={loadAccounts} />
    </>
  )
}
