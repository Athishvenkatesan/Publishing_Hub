import { useState } from "react"
import { Link } from "react-router"
import { Banner } from "@astryxdesign/core/Banner"
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import CheckAgain from "../components/CheckAgain.jsx"
import MetaTokenCard from "../components/MetaTokenCard.jsx"
import Nav from "../components/Nav.jsx"
import { metaMgrList } from "../lib/api.js"
import { useLoad } from "../lib/useLoad.js"

// The Meta accounts manager: the Facebook + Instagram token and the Threads token, each with its expiry, and the setup steps.
export default function MetaAccounts() {
  const { data, error, reload } = useLoad(metaMgrList, [])
  const [checked, setChecked] = useState(null)
  const [checking, setChecking] = useState(false)
  const check = () => { setChecking(true); reload().finally(() => { setChecking(false); setChecked(new Date()) }) }  // asks Meta about every token again
  return (
    <>
      <Nav />
      <header className="hero hero--fb">
        <div className="hero-copy">
          <span className="eyebrow eyebrow--light">Meta</span>
          <h1 className="hero-title">Accounts and tokens</h1>
          <p className="hero-sub">One card for all three Meta platforms: Facebook, Instagram and Threads. See who each token is and when it runs out, paste a new one, and make it last 60 days.</p>
        </div>
        <div className="hero-side">
          <Link className="hero-btn" to="/meta">Back to Meta</Link>
        </div>
      </header>
      <div className="page stack">
        {error && <Banner status="error" title="Could not load the tokens" description={error} />}
        <div className="grid grid--two grid--mgr">
          <div className="stack">
            {!data && !error && <Text color="secondary">Asking Meta about your tokens...</Text>}
            {data && (
              <article className="panel acct-card">
                <div className="meta-head">
                  <div><Heading level={3}>Meta</Heading><Text size="sm" color="secondary">Facebook, Instagram and Threads</Text></div>
                  <div className="step-aside"><CheckAgain inline onCheck={check} loading={checking} checked={checked} /></div>
                </div>
                <MetaTokenCard t={data.accounts.find((a) => a.key === "meta")} onChanged={reload} />
              </article>
            )}
          </div>
          {data && (
            <section className="panel">
              <Heading level={3}>Setting up</Heading>
              <Text size="sm" color="secondary">What you do once in Meta for Developers. This screen then shows what each token can reach.</Text>
              <ol className="guide">
                {data.guide.map((g) => (
                  <li key={g.title}>
                    <Text weight="semibold" size="sm">{g.title}</Text>
                    <Text size="sm" color="secondary">{g.do}</Text>
                    {g.link && <a className="linkbtn" href={g.link.url} target="_blank" rel="noreferrer">{g.link.label}</a>}
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>
      </div>
    </>
  )
}
