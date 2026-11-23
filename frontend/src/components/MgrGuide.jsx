// The steps a person does at the vendor (Google Cloud or the LinkedIn Developer portal), with the exact values to copy.
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"
import { KINDS } from "../lib/mgrKinds.js"

export default function MgrGuide({ guide, redirectUri, origin, kind = "youtube" }) {
  const k = KINDS[kind]
  const copy = (v) => navigator.clipboard?.writeText(v)
  return (
    <section className="panel">
      <Heading level={3}>Setting up an account</Heading>
      <Text size="sm" color="secondary">{`What you do once per ${k.appWord}. After the paste step this screen tells you what is still missing.`}</Text>
      <ol className="guide">
        {guide.map((g) => (
          <li key={g.title}>
            <Text weight="semibold" size="sm">{g.title}</Text>
            <Text size="sm" color="secondary">{g.do}</Text>
            {g.link && <a className="linkbtn" href={g.link.url} target="_blank" rel="noreferrer">{g.link.label}</a>}
          </li>
        ))}
      </ol>
      <div className="vals">
        <Text size="sm" weight="semibold">{k.valuesTitle}</Text>
        {origin && <div className="val"><div className="val-main"><Text size="sm" weight="semibold">Authorized JavaScript origins</Text><span className="mono">{origin}</span></div><button type="button" className="linkbtn" onClick={() => copy(origin)}>Copy</button></div>}
        <div className="val"><div className="val-main"><Text size="sm" weight="semibold">{k.redirectLabel}</Text><span className="mono">{redirectUri}</span></div><button type="button" className="linkbtn" onClick={() => copy(redirectUri)}>Copy</button></div>
      </div>
    </section>
  )
}
