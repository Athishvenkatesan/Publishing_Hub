// "Post to": a dropdown to tick one or several YouTube channels, a Connect button for signed-out
// accounts and "Add another channel".
import { useEffect, useRef, useState } from "react"
import { Link } from "react-router"
import { Badge } from "@astryxdesign/core/Badge"
import { Banner } from "@astryxdesign/core/Banner"
import { Text } from "@astryxdesign/core/Text"

export default function YtChannelPicker({ accounts, profiles, value, onChange, onAdd, onConnect, kids = null, noun = "channel", manageTo = "/youtube/accounts" }) {
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  useEffect(() => {
    if (!open) return
    const away = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false) }
    const esc = (e) => { if (e.key === "Escape") setOpen(false) }
    document.addEventListener("pointerdown", away); document.addEventListener("keydown", esc)
    return () => { document.removeEventListener("pointerdown", away); document.removeEventListener("keydown", esc) }
  }, [open])

  const by = (k) => profiles[k]
  const name = (a) => by(a.key)?.title || a.label
  const toggle = (k) => onChange(value.includes(k) ? value.filter((x) => x !== k) : [...value, k])
  const picked = accounts.filter((a) => value.includes(a.key))
  // A kids video on a channel that is not for kids (or the other way round) is easy to do by accident, so say it out loud.
  const odd = kids === null ? [] : picked.filter((a) => profiles[a.key] && profiles[a.key].kids_channel !== kids)
  const summary = !picked.length ? `Choose ${noun}s` : picked.length === 1 ? name(picked[0]) : `${picked.length} ${noun}s selected`

  return (
    <div className="stack">
      <Text size="sm" weight="semibold">Post to</Text>
      <div className="dd" ref={box}>
        <button type="button" className="dd-btn" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(!open)}>
          <span>{summary}</span><span aria-hidden="true">{open ? "▴" : "▾"}</span>
        </button>
        {open && (
          <div className="dd-menu" role="listbox" aria-multiselectable="true" aria-label={`${noun}s`}>
            {accounts.map((a) => {
              const p = by(a.key)
              return (
                <div key={a.key} className={`dd-row${a.connected ? "" : " dd-row--off"}`} role="option" aria-selected={value.includes(a.key)}>
                  <label className="chk">
                    <input type="checkbox" checked={value.includes(a.key)} disabled={!a.connected} onChange={() => toggle(a.key)} />
                    <span className="dd-text">
                      <b>{name(a)}</b>
                      <Text size="sm" color="secondary">{p ? `${p.handle || a.label} - ${a.label}` : a.label}</Text>
                      <span className="dd-badges">
                        {p?.kids_channel && <Badge variant="neutral" label="Kids channel" />}
                        {p && !p.verified && <Badge variant="warning" label="Not verified" />}
                      </span>
                    </span>
                  </label>
                  {!a.connected && a.configured && <button type="button" className="linkbtn" onClick={() => onConnect(a.key)}>Connect</button>}
                  {!a.configured && <Link className="linkbtn" to={manageTo}>Finish setup</Link>}
                </div>
              )
            })}
            <div className="dd-foot">
              <button type="button" className="linkbtn" onClick={() => { setOpen(false); onAdd() }}>+ Add another {noun}</button>
              <Link className="linkbtn" to={manageTo}>Manage accounts</Link>
            </div>
          </div>
        )}
      </div>
      {picked.length > 0 && (
        <div className="chips chips--row">
          {picked.map((a) => <button type="button" key={a.key} className="chip chip--on" title="Remove" onClick={() => toggle(a.key)}>{name(a)} {"×"}</button>)}
        </div>
      )}
      {odd.length > 0 && (
        <Banner status="warning" title={kids ? "Made for kids, but not a kids channel" : "A kids channel, but the video is not made for kids"}
          description={`${odd.map(name).join(", ")}: ${kids ? "this video is ticked Made for kids, and that channel is not marked for children." : "the video is not ticked Made for kids, and that channel is marked for children."} Check before you upload.`} />
      )}
      {value.length > 1 && <Text size="sm" color="secondary">The same video, details and time go to all {value.length} {noun}s. Each uses its own sign-in, and one failing does not stop the others.</Text>}
    </div>
  )
}
