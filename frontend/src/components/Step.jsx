// One numbered step card (the same look as the YouTube, LinkedIn and X screens). `aside` sits at the right end of the header.
import { Heading } from "@astryxdesign/core/Heading"

export default function Step({ n, title, children, dim, aside }) {
  return (
    <section className={`step${dim ? " step--dim" : ""}`}>
      <div className="step-head"><span className="step-n">{n}</span><Heading level={3}>{title}</Heading>{aside && <div className="step-aside">{aside}</div>}</div>
      {children}
    </section>
  )
}
