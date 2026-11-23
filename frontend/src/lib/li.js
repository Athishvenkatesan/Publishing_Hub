// Form state for the LinkedIn screen and how it becomes the post request.
export const TEXT_MAX = 3000
export const TITLE_MAX = 100
export const defaults = () => ({ text: "", title: "", visibility: "PUBLIC" })

export const applyAi = (f, li) => ({ ...f, text: li.text, title: li.title })

// With exactly one signed-in account there is nothing to choose, so it is ticked for you. With several, nothing is.
export const soleAccount = (accounts) => {
  const on = accounts.filter((a) => a.connected)
  return on.length === 1 ? on[0].key : null
}

// Picking one of the opening lines swaps the first paragraph and keeps the rest of the post.
export const withHook = (li, hook) => [hook, li.body, li.hashtags.map((h) => `#${h}`).join(" ")].filter(Boolean).join("\n\n")

export function toForm(file, f, accounts) {
  const d = new FormData()
  d.append("file", file); d.append("text", f.text); d.append("title", f.title); d.append("visibility", f.visibility)
  accounts.forEach((k) => d.append("accounts", k))
  return d
}
