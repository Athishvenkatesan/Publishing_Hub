import { describe, expect, it } from "vitest"
import { autoPlan } from "./allAuto.js"
import { META, metaAccounts, metaAuto } from "./metaAll.js"

const check = {
  pages: [{ id: "P1", name: "Gen Media AI ", tasks: ["CREATE_CONTENT"], instagram: { id: "IG1", username: "dgm" } }],
  capabilities: [{ key: "facebook_video", ok: true }, { key: "instagram_video", ok: true }, { key: "threads_video", ok: false, why: "Needs a Threads token." }],
}

describe("Meta on the combined screen", () => {
  it("lists the Page, the Instagram account and Threads, ready only where the token allows", () => {
    const a = metaAccounts(check)
    expect(a.map((x) => [x.key, x.label, x.connected])).toEqual([["P1", "Facebook - Gen Media AI", true], ["ig:IG1", "Instagram - @dgm", true], ["threads", "Threads", false]])
  })
  it("ticks every ready account after the analysis, but never Threads alone", () => {
    expect(metaAuto(metaAccounts(check))).toEqual(["P1", "ig:IG1"])
    expect(metaAuto([{ key: "threads", connected: true }])).toEqual([])
    expect(autoPlan({ kids: false, channels: null, youtubeAccounts: [], metaTargets: ["P1"] }).targets.meta).toEqual(["P1"])
    expect(autoPlan({ kids: false, channels: null, youtubeAccounts: [], metaTargets: ["P1"], hand: { accounts: { meta: true } } }).targets).toEqual({})
  })
  it("always posts now and sends Pages and Instagram apart", () => {
    const f = { ...META.defaults(), title: "T", text: "B", caption: "C", mode: "schedule" }
    expect(META.problem(f, ["P1", "ig:IG1"])).toBe("")
    const d = META.toForm(new Blob(["x"]), f, ["P1", "ig:IG1"])
    expect([d.get("mode"), d.getAll("pages"), d.getAll("instagram")]).toEqual(["now", ["P1"], ["IG1"]])
  })
})
