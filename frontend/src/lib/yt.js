// Form state for the YouTube screen and how it becomes the upload request.
export const defaults = () => ({
  title: "", description: "", tags: "", privacy: "public", categoryId: "22", madeForKids: false, language: "",
  license: "youtube", embeddable: true, publicStats: true, synthetic: false, notify: true,
})

export const applyAi = (f, y) => ({ ...f, title: y.title, description: y.description, tags: y.tags.join(", "), categoryId: y.category_id || f.categoryId })

export function toForm(file, f, thumb, mode, when, tz, accounts = []) {
  const d = new FormData()
  d.append("file", file); d.append("title", f.title); d.append("description", f.description); d.append("tags", f.tags)
  d.append("privacy", f.privacy); d.append("mode", mode); d.append("tz", tz)
  if (mode === "schedule") d.append("scheduled_at", when.slice(0, 16))
  d.append("category_id", f.categoryId); d.append("made_for_kids", String(f.madeForKids)); d.append("language", f.language)
  d.append("license", f.license); d.append("embeddable", String(f.embeddable)); d.append("public_stats", String(f.publicStats))
  d.append("synthetic", String(f.synthetic)); d.append("notify", String(f.notify))
  accounts.forEach((k) => d.append("accounts", k))
  if (thumb) d.append("thumbnail", thumb)
  return d
}

export const TITLE_MAX = 100
export const DESC_MAX = 5000
