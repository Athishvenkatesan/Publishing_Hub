import { describe as group, expect, it } from "vitest"
import { daysUntil, describe, fromIso, fromUnix, tone } from "./expiry.js"

const now = new Date(2026, 10, 24, 15, 0)  // 24 Nov 2026, afternoon

group("expiry dates", () => {
  it("counts whole days, whatever the time of day", () => {
    expect(daysUntil(fromIso("2026-11-25"), now)).toBe(1)
    expect(daysUntil(fromIso("2026-11-24"), now)).toBe(0)
    expect(daysUntil(fromIso("2026-11-20"), now)).toBe(-4)
  })
  it("says it in words and picks a colour", () => {
    expect(describe(fromIso("2027-01-15"), now)).toBe("15 Jan 2027 - 52 days left")
    expect(describe(fromIso("2026-11-23"), now)).toMatch("1 day ago")
    expect([tone(fromIso("2026-11-20"), now), tone(fromIso("2026-11-30"), now), tone(fromIso("2027-03-01"), now)]).toEqual(["error", "warning", "success"])
  })
  it("reads unix seconds and empty values", () => {
    expect(fromUnix(0)).toBe(null)
    expect(fromIso("")).toBe(null)
    expect(fromUnix(1795453200).getFullYear()).toBe(2026)
  })
})
