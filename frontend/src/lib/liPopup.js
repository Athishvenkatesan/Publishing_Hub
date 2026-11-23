// Sign-in in a small popup window, so the app page stays where it is (LinkedIn and X).
// The popup ends on #/<platform>/done, which tells this page the result and closes itself.
import { liConnect } from "./liApi.js"

// getLink(back) asks the backend for the sign-in link; `type` is the message the done page sends back.
export async function openSignIn(getLink, type) {
  const win = window.open("", type, "width=620,height=760")  // opened on the click itself, so the browser allows it
  let d
  try { d = await getLink(win ? "popup" : "accounts") } catch (e) { win?.close(); throw e }
  if (!win) { window.location.href = d.url; return new Promise(() => {}) }  // popups blocked: same sign-in, full page
  win.location.href = d.url
  return new Promise((resolve) => {
    const finish = (r) => { window.removeEventListener("message", onMsg); clearInterval(timer); resolve({ ...r, problem: d.problem }) }
    const onMsg = (e) => { if (e.origin === window.location.origin && e.data?.type === type) finish(e.data) }
    window.addEventListener("message", onMsg)
    const timer = setInterval(() => { if (win.closed) finish({ ok: false, closed: true }) }, 600)
  })
}

export const signInPopup = (key) => openSignIn((back) => liConnect(key, back), "linkedin-signin")

// What to tell the person when the popup did not end in a sign-in.
export const popupFailure = (r) => r.error || (r.problem ? `${r.problem} The sign-in window showed its own error for this reason.` : "The sign-in window was closed before the sign-in finished.")
