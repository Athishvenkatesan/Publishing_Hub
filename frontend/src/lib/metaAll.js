// Meta (Facebook + Instagram + Threads) as one platform on the combined screen. Its "accounts" come from the Meta token check:
// each Facebook Page, each linked Instagram account, and Threads. An account is "connected" when the token may post there; otherwise the picker shows "Finish setup" (the Meta screen).
import { createElement } from "react"
import MetaReview from "../components/MetaReview.jsx"
import { fbCheck, fbHistory, fbPublishMulti } from "./api.js"
import * as meta from "./meta.js"
import { TZ } from "./time.js"

export function metaAccounts(check) {
  const ok = (k) => !!check.capabilities.find((c) => c.key === k)?.ok
  const why = (k) => check.capabilities.find((c) => c.key === k)?.why || ""
  return [
    ...meta.postable(check.pages).map((p) => ({ key: p.id, label: `Facebook - ${p.name.trim()}`, configured: ok("facebook_video"), connected: ok("facebook_video"), why: why("facebook_video") })),
    ...meta.igAccounts(check.pages).map((a) => ({ key: a.key, label: `Instagram - @${a.username}`, configured: ok("instagram_video"), connected: ok("instagram_video"), why: why("instagram_video") })),
    { key: meta.THREADS, label: "Threads", configured: ok("threads_video"), connected: ok("threads_video"), why: why("threads_video") },
  ]
}

const Review = (props) => createElement(MetaReview, { ...props, showCaption: true })

export const META = {
  kind: "meta", aiKey: "facebook", name: "Meta", unit: "Account", accountsRoute: "/meta/accounts", screen: "/meta", Review,
  api: {
    accounts: () => fbCheck().then((c) => ({ accounts: metaAccounts(c) })),
    profiles: () => Promise.resolve({ profiles: [] }),
    history: fbHistory, publish: fbPublishMulti,
  },
  defaults: meta.defaults, applyAi: meta.applyAi,
  // Instagram and Threads post right away, so the combined screen always posts now.
  problem: (f, picked = []) => meta.problem({ ...f, mode: "now" }, picked),
  toForm: (file, f, accts) => meta.toForm(file, { ...f, mode: "now" }, accts, TZ),
  note: "Facebook, Instagram (as a Reel) and Threads. Posts right away. Open the Meta screen to schedule on Facebook.",
}

// After the AI has watched the video, every Meta account the token can post to is ticked (Threads only with another one).
export const metaAuto = (accounts) => {
  const on = accounts.filter((a) => a.connected).map((a) => a.key)
  return on.some((k) => k !== meta.THREADS) ? on : []
}
