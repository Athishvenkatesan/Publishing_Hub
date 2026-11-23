// What differs between the LinkedIn and X posting screens. PostPage and PostStudio read everything from here,
// so both screens look and behave the same (YouTube keeps its own, richer screen).
import LiPreviewCard from "../components/LiPreviewCard.jsx"
import LiPublish from "../components/LiPublish.jsx"
import LiReview from "../components/LiReview.jsx"
import XPreviewCard from "../components/XPreviewCard.jsx"
import XPublish from "../components/XPublish.jsx"
import XReview from "../components/XReview.jsx"
import * as li from "./li.js"
import { liAccounts, liAnalyze, liDelete, liDetails, liHistory, liProfiles, liPublishMulti, liRemove, liUpdate } from "./liApi.js"
import { signInPopup } from "./liPopup.js"
import * as x from "./x.js"
import { xAccounts, xAnalyze, xDelete, xDetails, xHistory, xProfiles, xPublishMulti, xRemove, xSignInPopup } from "./xApi.js"

export const LINKEDIN = {
  kind: "linkedin", name: "LinkedIn", heroClass: "hero--li", accountsRoute: "/linkedin/accounts", unit: "Profile", aiKey: "linkedin",
  hero: { lead: "Drop a video.", em: "AI writes the post.", tail: "Straight to LinkedIn.", sub: "Your local model watches the video and writes the post and hashtags. Review it, choose who it posts as, and publish." },
  upload: { accept: "video/mp4", description: "MP4, 3 seconds to 30 minutes, up to 300 MB.", working: "the LinkedIn post", note: "posts as a LinkedIn video" },
  api: { accounts: liAccounts, profiles: liProfiles, history: liHistory, remove: liRemove, analyze: liAnalyze, publish: liPublishMulti, details: liDetails, update: liUpdate, del: liDelete },
  defaults: li.defaults, applyAi: li.applyAi, toForm: li.toForm,
  problem: (f) => (!f.text.trim() ? "Write the post text." : f.text.length > li.TEXT_MAX ? `The post is over ${li.TEXT_MAX} characters.` : f.title.length > li.TITLE_MAX ? `The title is over ${li.TITLE_MAX} characters.` : ""),
  Review: LiReview, Publish: LiPublish, Preview: LiPreviewCard, popup: signInPopup, canEdit: true,
}

export const X = {
  kind: "x", name: "X", heroClass: "hero--x", accountsRoute: "/x/accounts", unit: "Profile", aiKey: "x",
  hero: { lead: "Drop a video.", em: "AI writes the post.", tail: "Straight to X.", sub: "Your local model watches the video and writes three short posts. Pick one, choose who it posts as, and publish." },
  upload: { accept: "video/mp4,video/quicktime", description: "MP4 or MOV, up to 300 MB here. X refuses videos longer than your account may post.", working: "three short posts", note: "posts as an X video" },
  api: { accounts: xAccounts, profiles: xProfiles, history: xHistory, remove: xRemove, analyze: xAnalyze, publish: xPublishMulti, details: xDetails, update: null, del: xDelete },
  defaults: x.defaults, applyAi: x.applyAi, toForm: x.toForm, problem: x.problem,
  Review: XReview, Publish: XPublish, Preview: XPreviewCard, popup: xSignInPopup, canEdit: false,
}
