import { describe, expect, it } from "vitest"
import { publishAll, retryOnly, summarise } from "./allPublish.js"

const ok = (name) => async () => ({ items: [{ account_name: name }], errors: [] })
const job = (kind, publish) => ({ kind, name: kind.toUpperCase(), publish, toForm: () => ({}), form: {}, accounts: ["a"] })

describe("publishAll", () => {
  it("posts platforms in order and keeps going when one throws", async () => {
    const order = []
    const jobs = [
      job("youtube", async () => { order.push("youtube"); return { items: [{ account_name: "Chan" }] } }),
      job("linkedin", async () => { order.push("linkedin"); throw new Error("token expired") }),
      job("x", async () => { order.push("x"); return { items: [{ account_name: "me" }] } }),
    ]
    const r = await publishAll(new Blob(["v"]), jobs)
    expect(order).toEqual(["youtube", "linkedin", "x"])
    expect(r.map((x) => x.items.length)).toEqual([1, 0, 1])
    expect(r[1].error).toBe("token expired")
  })
})

describe("summarise and retry", () => {
  it("is a success when every platform posted", async () => {
    const r = await publishAll(null, [job("youtube", ok("A")), job("x", ok("B"))])
    expect(summarise(r).status).toBe("success")
    expect(retryOnly(r)).toEqual(["youtube", "x"])
  })
  it("warns on a partial failure and retries only the failed platform", async () => {
    const r = await publishAll(null, [job("youtube", ok("A")), job("linkedin", async () => { throw new Error("nope") })])
    const s = summarise(r)
    expect(s.status).toBe("warning")
    expect(s.description).toContain("LINKEDIN: nope")
    expect(retryOnly(r)).toEqual(["youtube"])
  })
  it("is an error when nothing posted", async () => {
    const r = await publishAll(null, [job("x", async () => { throw new Error("no credits") })])
    expect(summarise(r)).toMatchObject({ status: "error", title: "Nothing was posted" })
  })
  it("treats a platform where one of its accounts failed as not finished", async () => {
    const r = await publishAll(null, [job("linkedin", async () => ({ items: [{ account_name: "A" }], errors: [{ label: "B", error: "bad" }] }))])
    expect(summarise(r).status).toBe("warning")
    expect(retryOnly(r)).toEqual([])
  })
})
