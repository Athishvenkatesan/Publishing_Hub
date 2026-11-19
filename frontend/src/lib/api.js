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
export const fbPublishPhoto = (form) => fetch("/api/facebook/photos", { method: "POST", body: form }).then(json)

export const ytStatus = () => fetch("/api/youtube/status").then(json)
export const ytConnect = () => fetch("/api/youtube/connect").then(json)
export const ytDisconnect = () => fetch("/api/youtube/disconnect", { method: "POST" }).then(json)
export const ytHistory = () => fetch("/api/youtube/posts").then(json)
export const ytPublish = (form) => fetch("/api/youtube/posts", { method: "POST", body: form }).then(json)
