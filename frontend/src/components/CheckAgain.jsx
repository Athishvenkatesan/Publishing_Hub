// "Check again": asks the platform(s) again and shows when it last did.
// `hero` styles it like the other buttons in a screen's header; `inline` is a small button for a card or step header.
import { Button } from "@astryxdesign/core/Button"
import { Text } from "@astryxdesign/core/Text"

const time = (d) => d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" })

export default function CheckAgain({ onCheck, loading, checked, hero, inline, note }) {
  if (inline) return (
    <>
      {checked && <Text size="sm" color="secondary">Last checked {time(checked)}</Text>}
      <Button variant="secondary" size="sm" label="Check again" isLoading={loading} onClick={onCheck} />
    </>
  )
  return (
    <div className={hero ? "check-again check-again--hero" : "btn-pair"}>
      {hero
        ? <button type="button" className="hero-btn" disabled={loading} onClick={onCheck}>{loading ? "Checking..." : "Check again"}</button>
        : <Button variant="secondary" label="Check again" isLoading={loading} onClick={onCheck} />}
      {checked && (hero ? <span className="check-again-time">Last checked {time(checked)}</span>
        : <Text size="sm" color="secondary">Last checked {time(checked)}.{note ? ` ${note}` : ""}</Text>)}
    </div>
  )
}
