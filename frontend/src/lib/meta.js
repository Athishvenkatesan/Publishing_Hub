// Form state for the Meta screen (Facebook Page video + Instagram Reel) and how it becomes the post request.
// Targets are one list: a Facebook Page id, or "ig:<instagram id>".
export const TITLE_MAX = 100
export const TEXT_MAX = 5000
export const CAPTION_MAX = 2200
export const defaults = () => ({ title: "", text: "", caption: "", mode: "now", when: undefined })

export const applyAi = (f, fb) => ({ ...f, title: fb.title, text: fb.text, caption: fb.caption || fb.text })

// Pages the token may post to. These are the "accounts" of this screen.
export const postable = (pages = []) => pages.filter((p) => p.tasks.includes("CREATE_CONTENT"))
// Instagram professional accounts linked to those Pages.
export const igAccounts = (pages = []) => pages.filter((p) => p.instagram).map((p) => ({ key: `ig:${p.instagram.id}`, username: p.instagram.username, page: p.name }))
export const isIg = (key) => key.startsWith("ig:")
export const THREADS = "threads"
export const THREADS_MAX = 500

// Once the AI has finished (or is not available), every Page and Instagram account the token can post to is ticked for you,
// unless the user already changed the ticks by hand.
export const autoTargets = ({ pages, fbReady = true, igReady, thReady = false, aiState, byHand, current }) => {
  if (byHand || !["done", "off"].includes(aiState)) return current
  const base = [...(fbReady ? postable(pages).map((p) => p.id) : []), ...(igReady ? igAccounts(pages).map((a) => a.key) : [])]
  return thReady && base.length ? [...base, THREADS] : base
}

export function problem(f, picked) {
  const ig = picked.some(isIg), th = picked.includes(THREADS), fb = picked.some((k) => !isIg(k) && k !== THREADS)
  if (!picked.length) return "Tick at least one Facebook Page, Instagram account or Threads."
  if (th && !ig && !fb) return "Threads needs Instagram or Facebook ticked too: it takes the video from that post."
  if (fb && !f.text.trim() && !f.title.trim()) return "Write a title or the post text."
  if ((ig || th) && !(f.caption || f.text).trim()) return "Write the caption."
  if (th && (f.caption || f.text).length > THREADS_MAX) return `Threads allows ${THREADS_MAX} characters. Shorten the caption.`
  if (f.title.length > TITLE_MAX) return `The title is over ${TITLE_MAX} characters.`
  if (f.text.length > TEXT_MAX) return `The post text is over ${TEXT_MAX} characters.`
  if (ig && f.caption.length > CAPTION_MAX) return `The Instagram caption is over ${CAPTION_MAX} characters.`
  if (f.mode === "schedule" && (ig || th)) return "Instagram and Threads post right away. Untick them to schedule, or choose Publish now."
  if (f.mode === "schedule" && !f.when) return "Pick a date and time."
  return ""
}

export function toForm(file, f, targets, tz) {
  const d = new FormData()
  d.append("file", file); d.append("title", f.title); d.append("description", f.text); d.append("caption", f.caption || f.text)
  d.append("mode", f.mode); d.append("tz", tz)
  if (f.mode === "schedule") d.append("scheduled_at", f.when.slice(0, 16))
  targets.forEach((k) => (k === THREADS ? d.append("threads", "true") : isIg(k) ? d.append("instagram", k.slice(3)) : d.append("pages", k)))
  return d
}
