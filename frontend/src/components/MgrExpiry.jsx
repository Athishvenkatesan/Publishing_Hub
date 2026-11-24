// The expiry lines on an account card: when the sign-in or token runs out (from the platform), and the person's own expiry date.
import { Badge } from "@astryxdesign/core/Badge"
import { Text } from "@astryxdesign/core/Text"
import { describe, fromIso, fromUnix, tone } from "../lib/expiry.js"

function Line({ label, date, note }) {
  return (
    <div className="exp-line">
      <Text size="sm" weight="semibold">{label}</Text>
      {date ? <Badge variant={tone(date)} label={describe(date)} /> : <Text size="sm" color="secondary">{note}</Text>}
    </div>
  )
}

export default function MgrExpiry({ signinAt, signinNote, never, expiresOn, what = "Sign-in expires" }) {
  const signin = fromUnix(signinAt), own = fromIso(expiresOn)
  return (
    <div className="exp">
      {(signin || signinNote || never) && <Line label={signin || never ? what : what.split(" ")[0]} date={signin} note={never ? "Never (no end date)" : signinNote} />}
      {signin && signinNote && <Text size="sm" color="secondary">{signinNote}</Text>}
      <Line label="Your expiry date" date={own} note="Not set. Add one with Edit." />
    </div>
  )
}
