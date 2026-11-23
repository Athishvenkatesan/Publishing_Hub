import { describe, expect, it } from "vitest"
import { applyAi, autoTargets, defaults, problem, THREADS, toForm } from "./meta.js"

const pages = [{ id: "P1", name: "Page", tasks: ["CREATE_CONTENT"], instagram: { id: "IG1", username: "dgm" } }, { id: "P2", tasks: ["ANALYZE"] }]

describe("Meta form", () => {
  it("ticks Pages and ready Instagram accounts only after the AI is done, and never over a manual choice", () => {
    expect(autoTargets({ pages, igReady: true, aiState: "working", byHand: false, current: [] })).toEqual([])
    expect(autoTargets({ pages, igReady: true, aiState: "done", byHand: false, current: [] })).toEqual(["P1", "ig:IG1"])
    expect(autoTargets({ pages, igReady: false, aiState: "done", byHand: false, current: [] })).toEqual(["P1"])
    expect(autoTargets({ pages, igReady: true, aiState: "done", byHand: true, current: [] })).toEqual([])
    expect(autoTargets({ pages, igReady: true, thReady: true, aiState: "done", byHand: false, current: [] })).toEqual(["P1", "ig:IG1", THREADS])
  })
  it("needs a target, some text, and no schedule when Instagram is ticked", () => {
    expect(problem(defaults(), [])).toMatch("Tick")
    expect(problem(defaults(), ["P1"])).toMatch("Write")
    const f = applyAi(defaults(), { title: "T", text: "Hi #A", caption: "Short #A" })
    expect(problem(f, ["P1", "ig:IG1"])).toBe("")
    expect(problem({ ...f, mode: "schedule", when: "2026-12-01T10:30" }, ["P1", "ig:IG1"])).toMatch("Instagram and Threads post right away")
    expect(problem({ ...f, mode: "schedule" }, ["P1"])).toMatch("date")
  })
  it("splits Pages and Instagram accounts and sends the caption", () => {
    const d = toForm(new Blob(["x"]), { title: "T", text: "B", caption: "C", mode: "now" }, ["P1", "ig:IG1"], "Asia/Dubai")
    expect(d.getAll("pages")).toEqual(["P1"])
    expect(d.getAll("instagram")).toEqual(["IG1"])
    expect(d.get("caption")).toBe("C")
    expect(toForm(new Blob(["x"]), { title: "", text: "", caption: "C", mode: "now" }, ["ig:IG1", THREADS], "UTC").get("threads")).toBe("true")
  })
  it("Threads needs another platform and a short caption", () => {
    const f = { ...defaults(), caption: "x".repeat(501) }
    expect(problem(f, [THREADS])).toMatch("needs Instagram or Facebook")
    expect(problem(f, ["ig:IG1", THREADS])).toMatch("500")
  })
})
