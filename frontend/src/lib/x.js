// Form state for the X screen and how it becomes the post request.
export const TEXT_SOFT = 280      // a normal X account; Premium accounts may post longer
export const TEXT_MAX = 25000
export const defaults = () => ({ text: "", reply: "everyone" })
export const applyAi = (f, x) => ({ ...f, text: x.text })
export const problem = (f) => (!f.text.trim() ? "Write the post text." : f.text.length > TEXT_MAX ? `The post is over ${TEXT_MAX} characters.` : "")

export function toForm(file, f, accounts) {
  const d = new FormData()
  d.append("file", file); d.append("text", f.text); d.append("reply", f.reply)
  accounts.forEach((k) => d.append("accounts", k))
  return d
}
