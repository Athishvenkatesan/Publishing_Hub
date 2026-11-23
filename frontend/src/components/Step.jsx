// One numbered step card (the same look as the YouTube, LinkedIn and X screens).
import { Heading } from "@astryxdesign/core/Heading"

export default function Step({ n, title, children, dim }) {
  return (
    <section className={`step${dim ? " step--dim" : ""}`}>
      <div className="step-head"><span className="step-n">{n}</span><Heading level={3}>{title}</Heading></div>
      {children}
    </section>
  )
}
