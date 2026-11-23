// X calls (same shape as liApi.js). The chosen account rides along as ?account=key.
import { openSignIn } from "./liPopup.js"

async function json(res) {
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`)
  return body
}
const body = (method, data) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })

export const xAccounts = () => fetch("/api/x/accounts").then(json)
export const xProfiles = () => fetch("/api/x/channels/profiles").then(json)
export const xHistory = () => fetch("/api/x/posts").then(json)
export const xPublishMulti = (form) => fetch("/api/x/posts/multi", { method: "POST", body: form }).then(json)
export const xDetails = (id) => fetch(`/api/x/posts/${id}/details`).then(json)
export const xDelete = (id) => fetch(`/api/x/posts/${id}`, { method: "DELETE" }).then(json)
export const xRemove = (id) => fetch(`/api/x/posts/${id}/local`, { method: "DELETE" }).then(json)
export const xConnect = (key, back = "accounts") => fetch("/api/x/connect?" + new URLSearchParams({ account: key, back })).then(json)
export const xDisconnect = (key) => fetch(`/api/x/disconnect?account=${encodeURIComponent(key)}`, { method: "POST" }).then(json)
export const xSignInPopup = (key) => openSignIn((back) => xConnect(key, back), "x-signin")

export function xAnalyze(file, lang, hint) {
  const f = new FormData()
  f.append("file", file); f.append("lang", lang); f.append("hint", hint)
  return fetch("/api/analyze/x", { method: "POST", body: f }).then(json)
}

const mgr = (path, init) => fetch(`/api/x/manager/${path}`, init).then(json)
export const xMgrList = () => mgr("accounts")
export const xMgrAdd = (data) => mgr("accounts", body("POST", data))
export const xMgrEdit = (key, data) => mgr(`accounts/${key}`, body("PATCH", data))
export const xMgrDelete = (key) => mgr(`accounts/${key}`, { method: "DELETE" })
export const xMgrCheck = (key) => mgr(`accounts/${key}/check`)
