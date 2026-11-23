// The platforms on the combined screen (YouTube, LinkedIn, X, Meta): what each one is called, which calls it uses, and how its form is built.
import LiReview from "../components/LiReview.jsx"
import XReview from "../components/XReview.jsx"
import YtReview from "../components/YtReview.jsx"
import { ytAccounts, ytChannelProfiles, ytHistory, ytPublishMulti } from "./api.js"
import * as li from "./li.js"
import { liAccounts, liHistory, liProfiles, liPublishMulti } from "./liApi.js"
import { TZ } from "./time.js"
import * as x from "./x.js"
import { META } from "./metaAll.js"
import { xAccounts, xHistory, xProfiles, xPublishMulti } from "./xApi.js"
import * as yt from "./yt.js"

const ytProblem = (f) => (!f.title.trim() ? "YouTube needs a title." : f.title.length > yt.TITLE_MAX ? "The YouTube title is over 100 characters."
  : f.description.length > yt.DESC_MAX ? "The YouTube description is over 5,000 characters." : "")

// YouTube here posts now and public; thumbnails, categories and scheduling stay on the YouTube screen.
const ytApply = (cur, d) => ({ ...yt.applyAi(cur, d), madeForKids: d.suggestions?.made_for_kids?.value ?? cur.madeForKids, synthetic: d.suggestions?.ai_generated?.value ?? cur.synthetic })

export const PLATFORMS = [
  { kind: "youtube", name: "YouTube", unit: "Channel", accountsRoute: "/youtube/accounts", screen: "/youtube", Review: YtReview,
    api: { accounts: ytAccounts, profiles: ytChannelProfiles, history: ytHistory, publish: ytPublishMulti },
    defaults: yt.defaults, applyAi: ytApply, problem: ytProblem, toForm: (file, f, accts) => yt.toForm(file, f, null, "now", undefined, TZ, accts),
    note: "Uploads now as public. Open the YouTube screen for a thumbnail, a category or a schedule." },
  { kind: "linkedin", name: "LinkedIn", unit: "Profile", accountsRoute: "/linkedin/accounts", screen: "/linkedin", Review: LiReview,
    api: { accounts: liAccounts, profiles: liProfiles, history: liHistory, publish: liPublishMulti },
    defaults: li.defaults, applyAi: li.applyAi, toForm: li.toForm,
    problem: (f) => (!f.text.trim() ? "Write the LinkedIn text." : f.text.length > li.TEXT_MAX ? `The LinkedIn post is over ${li.TEXT_MAX} characters.` : ""),
    note: "Posts right away (LinkedIn has no scheduling for apps)." },
  { kind: "x", name: "X", unit: "Profile", soon: true,  // shown, but posting to X is switched off for now
    accountsRoute: "/x/accounts", screen: "/x", Review: XReview,
    api: { accounts: xAccounts, profiles: xProfiles, history: xHistory, publish: xPublishMulti },
    defaults: x.defaults, applyAi: x.applyAi, toForm: x.toForm, problem: x.problem,
    note: "Coming soon. X is shown here, but posting to X is switched off for now." },
  META,
]
export const aiKey = (p) => p.aiKey || p.kind  // which part of the AI answer is this platform's draft

export async function allAnalyze(file, lang, hint) {
  const f = new FormData()
  f.append("file", file); f.append("lang", lang); f.append("hint", hint)
  const res = await fetch("/api/analyze/all", { method: "POST", body: f })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`)
  return body
}

// Each platform's own AI draft: { youtube, linkedin, x, facebook } -> its form.
export const draftsToForms = (d, cur) => Object.fromEntries(PLATFORMS.map((p) => [p.kind, d[aiKey(p)] ? p.applyAi(cur[p.kind], d[aiKey(p)]) : cur[p.kind]]))
export const freshForms = () => Object.fromEntries(PLATFORMS.map((p) => [p.kind, p.defaults()]))
