// Step: where it goes (Facebook Pages, Instagram accounts and Threads, ticked by the AI once each is ready on its token),
// when, and the one Publish button.
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"
import { THREADS, igAccounts, isIg, postable } from "../lib/meta.js"
import FbWhen from "./FbWhen.jsx"

function Row({ checked, disabled, onChange, title, sub }) {
  return (
    <label className={`chk${disabled ? " dd-row--off" : ""}`}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={onChange} />
      <span className="dd-text"><b>{title}</b><Text size="sm" color="secondary">{sub}</Text></span>
    </label>
  )
}

export default function MetaPublish({ f, setF, pages, caps, value, onChange, auto, busy, problem, onPublish }) {
  const cap = (k) => caps.find((c) => c.key === k)
  const fbOk = !!cap("facebook_video")?.ok, igOk = !!cap("instagram_video")?.ok, thOk = !!cap("threads_video")?.ok
  const toggle = (id) => onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id])
  const ig = igAccounts(pages)
  const names = [...postable(pages).filter((p) => value.includes(p.id)).map((p) => `Facebook ${p.name.trim()}`),
    ...ig.filter((a) => value.includes(a.key)).map((a) => `Instagram @${a.username}`), ...(value.includes(THREADS) ? ["Threads"] : [])]
  const igPicked = value.some(isIg) || value.includes(THREADS)
  const label = f.mode === "schedule" ? "Schedule on Facebook" : value.length > 1 ? "Publish to all ticked" : "Publish"
  return (
    <div className="stack">
      <Text size="sm" weight="semibold">Post to</Text>
      {cap("facebook_video") && !fbOk && <Banner status="warning" title="This token cannot post to Facebook yet" description={cap("facebook_video").why} />}
      {postable(pages).map((p) => <Row key={p.id} checked={value.includes(p.id)} disabled={!fbOk} onChange={() => toggle(p.id)} title={`Facebook - ${p.name.trim()}`} sub={p.category || "Facebook Page"} />)}
      {ig.map((a) => <Row key={a.key} checked={value.includes(a.key)} disabled={!igOk} onChange={() => toggle(a.key)} title={`Instagram - @${a.username}`}
        sub={igOk ? `Posts as a Reel, right away. Linked to ${a.page.trim()}.` : cap("instagram_video")?.why} />)}
      {!ig.length && <Row checked={false} disabled title="Instagram" sub={cap("instagram_video")?.why || "No Instagram account is linked to your Page."} />}
      <Row checked={value.includes(THREADS)} disabled={!thOk} onChange={() => toggle(THREADS)} title="Threads"
        sub={thOk ? `${cap("threads_video").why} Posts right away, max 500 characters, using the video from the Instagram or Facebook post.` : cap("threads_video")?.why || "Not available yet."} />
      {auto && <Text size="sm" color="secondary">Ticked for you after the analysis. Untick anything you do not want.</Text>}
      <FbWhen mode={f.mode} setMode={(m) => setF({ ...f, mode: m })} when={f.when} setWhen={(w) => setF({ ...f, when: w })}
        note={igPicked ? "Facebook needs 10 minutes to 75 days ahead. Instagram and Threads cannot be scheduled from apps." : undefined} />
      <Button size="lg" label={label + (value.length > 1 ? ` (${value.length})` : "")} isLoading={busy} isDisabled={!!problem || busy} onClick={onPublish} />
      {!problem && names.length > 0 && <Text size="sm" weight="semibold">{f.mode === "now" ? "Will post" : "Will schedule"} to {names.join(" and ")}.</Text>}
      {problem && <Text size="sm" color="secondary">{problem}</Text>}
      {busy && <Text size="sm" color="secondary">Uploading. Instagram processes a Reel before posting it, so this can take a few minutes.</Text>}
    </div>
  )
}
