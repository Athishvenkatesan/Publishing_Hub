export const TZ = "Asia/Dubai"

// "YYYY-MM-DDTHH:mm" for a Date as seen in a time zone (DateTimeInput format).
export function localInZone(date = new Date(), tz = TZ) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit",
      day: "2-digit", hour: "2-digit", minute: "2-digit" }).formatToParts(date).map((x) => [x.type, x.value]))
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`
}

export const fmt = (iso, tz = TZ) =>
  iso ? new Intl.DateTimeFormat("en-GB", { timeZone: tz, dateStyle: "medium", timeStyle: "short" }).format(new Date(iso)) : "-"
