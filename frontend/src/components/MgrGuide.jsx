// The steps a person does in Google Cloud, with the exact values to copy.
import { Heading } from "@astryxdesign/core/Heading"
import { Text } from "@astryxdesign/core/Text"

export default function MgrGuide({ guide, redirectUri, origin }) {
  const copy = (v) => navigator.clipboard?.writeText(v)
  return (
    <section className="panel">
      <Heading level={3}>Setting up an account</Heading>
      <Text size="sm" color="secondary">What you do once per Google app. After step 5 this screen tells you what is still missing.</Text>
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
        <Text size="sm" weight="semibold">Values Google may ask for</Text>
        <div className="val"><span className="mono">{redirectUri}</span><button type="button" className="linkbtn" onClick={() => copy(redirectUri)}>Copy redirect address</button></div>
        <div className="val"><span className="mono">{origin}</span><button type="button" className="linkbtn" onClick={() => copy(origin)}>Copy JavaScript origin</button></div>
      </div>
    </section>
  )
}
