// LinkedIn calls. The chosen account rides along on every call as ?account=key (same idea as the YouTube helpers in api.js).
async function json(res) {
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`)
  return body
}
const body = (method, data) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })

export const liAccounts = () => fetch("/api/linkedin/accounts").then(json)
export const liProfiles = () => fetch("/api/linkedin/channels/profiles").then(json)
export const liHistory = () => fetch("/api/linkedin/posts").then(json)
export const liPublishMulti = (form) => fetch("/api/linkedin/posts/multi", { method: "POST", body: form }).then(json)
export const liDetails = (id) => fetch(`/api/linkedin/posts/${id}/details`).then(json)
export const liUpdate = (id, data) => fetch(`/api/linkedin/posts/${id}`, body("PATCH", data)).then(json)
export const liDelete = (id) => fetch(`/api/linkedin/posts/${id}`, { method: "DELETE" }).then(json)
export const liRemove = (id) => fetch(`/api/linkedin/posts/${id}/local`, { method: "DELETE" }).then(json)

// Start the LinkedIn sign-in for one account and come back to `back` (accounts | linkedin) afterwards.
export const liConnect = (key, back = "accounts") => fetch("/api/linkedin/connect?" + new URLSearchParams({ account: key, back, check: "true" })).then(json)
// Sign in with a token made in the LinkedIn Developer portal (no redirect URL needed).
export const liToken = (key, token) => fetch(`/api/linkedin/token?account=${encodeURIComponent(key)}`, body("POST", { access_token: token })).then(json)
export const liDisconnect = (key) => fetch(`/api/linkedin/disconnect?account=${encodeURIComponent(key)}`, { method: "POST" }).then(json)

export function liAnalyze(file, lang, hint) {
  const f = new FormData()
  f.append("file", file); f.append("lang", lang); f.append("hint", hint)
  return fetch("/api/analyze/linkedin", { method: "POST", body: f }).then(json)
}

// Accounts manager
const mgr = (path, init) => fetch(`/api/linkedin/manager/${path}`, init).then(json)
export const liMgrList = () => mgr("accounts")
export const liMgrAdd = (data) => mgr("accounts", body("POST", data))
export const liMgrEdit = (key, data) => mgr(`accounts/${key}`, body("PATCH", data))
export const liMgrDelete = (key) => mgr(`accounts/${key}`, { method: "DELETE" })
export const liMgrCheck = (key) => mgr(`accounts/${key}/check`)
export const liMgrValues = (key) => mgr(`accounts/${key}/values`)
