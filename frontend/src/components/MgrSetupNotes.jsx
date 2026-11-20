// Shown in the Add account panel: the two addresses to register in Google, and the three email checks before signing in.
import { Text } from "@astryxdesign/core/Text"

function Value({ field, value }) {
  return (
    <div className="val">
      <div className="val-main"><Text size="sm" weight="semibold">{field}</Text><span className="mono">{value}</span></div>
      <button type="button" className="linkbtn" onClick={() => navigator.clipboard?.writeText(value)}>Copy</button>
    </div>
  )
}

export default function MgrSetupNotes({ origin, redirectUri, email }) {
  const who = email.includes("@") ? email : "this Gmail"
  return (
    <>
      <div className="vals">
        <Text size="sm" weight="semibold">When you create the client ID and secret (Web application)</Text>
        <Value field="1. Authorized JavaScript origins" value={origin} />
        <Value field="2. Authorized redirect URIs" value={redirectUri} />
        <Text size="sm" color="secondary">Paste each into its own box in Google. They are not interchangeable. A Desktop app client needs neither.</Text>
      </div>
      <section className="warn-note" role="alert">
        <div className="warn-head"><span className="warn-icon" aria-hidden="true">!</span><b>Before you press Connect</b></div>
        <p>You are adding {who}. Check these three things first:</p>
        <ol>
          <li>Be signed in to {who} in this browser. Google signs in whichever account the browser is using.</li>
          <li>In Google Auth Platform, Audience, Test users: {who} must be in the list.</li>
          <li>In Branding, App information, User support email: use the same email, so the app, the test user and the channel owner all match.</li>
        </ol>
        <p>Then add the account here, press Connect and sign in.</p>
      </section>
    </>
  )
}
