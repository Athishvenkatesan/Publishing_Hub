// Small fetch helpers. Errors carry the backend's message so the UI can show it.
async function json(res) {
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`)
  return body
}
export const getAccounts = () => fetch("/api/accounts").then(json)
export const getHistory = () => fetch("/api/posts").then(json)
export const createPost = (form) => fetch("/api/posts", { method: "POST", body: form }).then(json)

export const analyzeStatus = () => fetch("/api/analyze/status").then(json)
export function analyzeVideo(file, lang, hint) {
  const f = new FormData()
  f.append("file", file); f.append("lang", lang); f.append("hint", hint)
  return fetch("/api/analyze", { method: "POST", body: f }).then(json)
}

export const connectAccount = (platform) => fetch("/api/accounts/connect", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ platform, return_to: window.location.origin + "/?connected=1" }) }).then(json)
export const disconnectAccount = (id) => fetch(`/api/accounts/${id}`, { method: "DELETE" }).then(json)

export const fbCheck = () => fetch("/api/facebook/check").then(json)
export const fbHistory = () => fetch("/api/facebook/posts").then(json)
export const fbPublish = (form) => fetch("/api/facebook/posts", { method: "POST", body: form }).then(json)
export const fbPublishMulti = (form) => fetch("/api/facebook/posts/multi", { method: "POST", body: form }).then(json)
export function fbAnalyze(file, lang, hint) {
  const f = new FormData()
  f.append("file", file); f.append("lang", lang); f.append("hint", hint)
  return fetch("/api/analyze/meta", { method: "POST", body: f }).then(json)
}

// The chosen YouTube account rides along on every YouTube call as ?account=key.
let ytAccount = ""
export const setYtAccount = (key) => { ytAccount = key || "" }
const yta = (url) => (ytAccount ? `${url}${url.includes("?") ? "&" : "?"}account=${encodeURIComponent(ytAccount)}` : url)
export const ytAccounts = () => fetch("/api/youtube/accounts").then(json)
export const ytStatus = () => fetch(yta("/api/youtube/status")).then(json)
export const ytConnect = (opts = {}) => fetch(yta("/api/youtube/connect?" + new URLSearchParams({ check: "true", ...opts }))).then(json)
export const ytDisconnect = () => fetch(yta("/api/youtube/disconnect"), { method: "POST" }).then(json)
export const ytHistory = () => fetch("/api/youtube/posts").then(json)
export const ytPublish = (form) => fetch(yta("/api/youtube/posts"), { method: "POST", body: form }).then(json)

export function ytAnalyze(file, lang, hint) {
  const f = new FormData()
  f.append("file", file); f.append("lang", lang); f.append("hint", hint)
  return fetch("/api/analyze/youtube", { method: "POST", body: f }).then(json)
}

const jsonBody = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
export const ytDetails = (id) => fetch(`/api/youtube/posts/${id}/details`).then(json)
export const ytUpdate = (id, body) => fetch(`/api/youtube/posts/${id}`, jsonBody("PATCH", body)).then(json)
export const ytDelete = (id) => fetch(`/api/youtube/posts/${id}`, { method: "DELETE" }).then(json)
export const ytRemove = (id) => fetch(`/api/youtube/posts/${id}/local`, { method: "DELETE" }).then(json)

export function ytThumbCandidates(file, lang, hint, description, title) {
  const f = new FormData()
  f.append("file", file); f.append("lang", lang); f.append("hint", hint); f.append("description", description); f.append("title", title)
  return fetch("/api/thumbnails/candidates", { method: "POST", body: f }).then(json)
}
export async function ytThumbRender(body) {
  const res = await fetch("/api/thumbnails/render", jsonBody("POST", body))
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Request failed (${res.status})`)
  return res.blob()
}

// Studio management (read-only views of the channel)
const studio = (path) => fetch(yta(`/api/youtube/studio/${path}`)).then(json)
export const studioOverview = () => studio("overview")
export const studioVideos = (token = "") => studio(`videos${token ? "?page_token=" + encodeURIComponent(token) : ""}`)
export const studioPlaylists = () => studio("playlists")
export const studioAccess = () => studio("access")
export const studioReports = (days) => studio(`reports?days=${days}`)

// Accounts manager (works on any account by key, whichever one is active)
const mgr = (path, init) => fetch(`/api/youtube/manager/${path}`, init).then(json)
export const mgrList = () => mgr("accounts")
export const mgrAdd = (body) => mgr("accounts", jsonBody("POST", body))
export const mgrEdit = (key, body) => mgr(`accounts/${key}`, jsonBody("PATCH", body))
export const mgrDelete = (key) => mgr(`accounts/${key}`, { method: "DELETE" })
export const mgrCheck = (key) => mgr(`accounts/${key}/check`)
export const mgrValues = (key) => mgr(`accounts/${key}/values`)
// Start Google sign-in for one account and return to `back` (accounts | studio) afterwards.
export const connectAccount_ = (key, opts = {}, back = "accounts") =>
  fetch("/api/youtube/connect?" + new URLSearchParams({ account: key, back, check: "true", ...opts })).then(json)
export const studioUrl = (path) => yta(`/api/youtube/studio/${path}`)  // for download links
export const ytPublishMulti = (form) => fetch("/api/youtube/posts/multi", { method: "POST", body: form }).then(json)

// Channels: who each signed-in channel is, and which ones fit a video
export const ytChannelProfiles = () => fetch("/api/youtube/channels/profiles").then(json)
export const ytSuggestChannels = (body) => fetch("/api/youtube/channels/suggest", jsonBody("POST", body)).then(json)

// Meta accounts manager (the Facebook + Instagram token and the Threads token)
const metaMgr = (path, init) => fetch(`/api/meta/manager/${path}`, init).then(json)
export const metaMgrList = () => metaMgr("accounts")
export const metaMgrEdit = (key, data) => metaMgr(`accounts/${key}`, jsonBody("PATCH", data))
export const metaMgrValues = (key) => metaMgr(`accounts/${key}/values`)
export const metaMgrRemove = () => metaMgr("accounts/meta", { method: "DELETE" })
export const metaMgrExtend = (key) => metaMgr(`accounts/${key}/extend`, { method: "POST" })
