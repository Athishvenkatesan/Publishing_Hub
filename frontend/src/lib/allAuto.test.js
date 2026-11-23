import { describe, expect, it } from "vitest"
import { autoPlan } from "./allAuto.js"

const yt = [{ key: "a", connected: true }, { key: "kids", connected: true }, { key: "out", connected: false }]
const channels = { recommended: ["kids", "out"], ranked: [{ key: "kids", label: "Kids channel", reason: "a kids channel, and this video is made for kids" }] }

describe("autoPlan", () => {
  it("ticks the suggested signed-in YouTube channels and says why", () => {
    const p = autoPlan({ kids: false, channels, youtubeAccounts: yt })
    expect(p.targets.youtube).toEqual(["kids"])  // "out" is not signed in
    expect(p.why.youtube).toContain("Kids channel")
    expect(p.off).toEqual([])
  })
  it("switches LinkedIn off for a kids video", () => {
    const p = autoPlan({ kids: true, channels: null, youtubeAccounts: yt })
    expect(p.off).toEqual(["linkedin"])
    expect(p.why.linkedin).toMatch("kids")
    expect(p.targets).toEqual({})
  })
  it("never overrides what the person changed by hand", () => {
    const p = autoPlan({ kids: true, channels, youtubeAccounts: yt, hand: { platforms: { linkedin: true }, accounts: { youtube: true } } })
    expect(p).toEqual({ off: [], targets: {}, why: {} })
  })
  it("ticks nothing when there is no suggestion", () => {
    expect(autoPlan({ kids: false, channels: { recommended: [], ranked: [] }, youtubeAccounts: yt }).targets).toEqual({})
  })
})
