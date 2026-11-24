// Expiry dates on the account managers: a sign-in or token end (unix seconds) and the person's own date (YYYY-MM-DD).
const DAY = 86400000

export const fmtDay = (d) => d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })

// Whole days from today to the date (negative once it has passed).
export function daysUntil(date, now = new Date()) {
  const a = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const b = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  return Math.round((b - a) / DAY)
}

// "15 Jan 2027 - 52 days left", "today", "3 days ago".
export function describe(date, now = new Date()) {
  const n = daysUntil(date, now)
  const left = n > 1 ? `${n} days left` : n === 1 ? "tomorrow" : n === 0 ? "today" : n === -1 ? "1 day ago" : `${-n} days ago`
  return `${fmtDay(date)} - ${left}`
}

// Badge colour: passed = error, within a week = warning, otherwise fine.
export const tone = (date, now = new Date()) => {
  const n = daysUntil(date, now)
  return n < 0 ? "error" : n <= 7 ? "warning" : "success"
}

export const fromUnix = (s) => (s ? new Date(s * 1000) : null)
export const fromIso = (s) => (s ? new Date(`${s}T00:00:00`) : null)
