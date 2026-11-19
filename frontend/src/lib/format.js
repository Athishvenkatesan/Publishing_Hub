// Number and date formatting for the Studio screens.
export const compact = (n) => (n == null || Number.isNaN(n) ? "-" : Math.abs(n) < 10000 ? Math.round(n).toLocaleString("en-US")
  : new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(n))

export const duration = (s) => {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = Math.round(s % 60)
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}` : `${m}:${String(sec).padStart(2, "0")}`
}

export const shortDate = (iso) => (iso ? new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(iso)) : "-")
export const longDate = (iso) => (iso ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "Asia/Dubai" }).format(new Date(iso)) : "-")

// Change against the previous period, as text and direction (no colour-only meaning).
export function change(cur, prev) {
  if (cur == null || prev == null) return null
  if (prev === 0) return cur === 0 ? { text: "no change", dir: 0 } : { text: "new", dir: 1 }
  const p = ((cur - prev) / Math.abs(prev)) * 100
  return { text: `${p > 0 ? "+" : ""}${p.toFixed(Math.abs(p) < 10 ? 1 : 0)}%`, dir: Math.sign(p) }
}

export const AGE = (a) => a.replace("age", "").replace("-", " to ").replace("65-", "65+")
export const TRAFFIC = { YT_SEARCH: "YouTube search", SUGGESTED_VIDEO: "Suggested videos", BROWSE: "Browse features", EXT_URL: "External sites",
  NOTIFICATION: "Notifications", SHORTS: "Shorts feed", YT_CHANNEL: "Channel pages", PLAYLIST: "Playlists", NO_LINK_OTHER: "Direct or unknown",
  YT_OTHER_PAGE: "Other YouTube pages", END_SCREEN: "End screens", HASHTAGS: "Hashtag pages", SUBSCRIBER: "Subscriptions feed" }
export const label = (map, k) => map[k] || k.toLowerCase().replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())
