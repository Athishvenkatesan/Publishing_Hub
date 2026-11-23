import { describe, expect, it } from "vitest"
import { applyAi, defaults, problem, TEXT_MAX } from "./x.js"

describe("X form", () => {
  it("needs text and allows up to the Premium limit", () => {
    expect(problem(defaults())).toBe("Write the post text.")
    expect(problem({ ...defaults(), text: "x".repeat(300) })).toBe("")  // over 280 is only a warning: Premium accounts may post it
    expect(problem({ ...defaults(), text: "x".repeat(TEXT_MAX + 1) })).toMatch("over")
  })
  it("takes the AI's first option and keeps the reply setting", () => {
    expect(applyAi({ text: "", reply: "following" }, { text: "Hi #A", options: ["Hi #A"] })).toEqual({ text: "Hi #A", reply: "following" })
  })
})
