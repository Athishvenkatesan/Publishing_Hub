import { describe, expect, it } from "vitest"
import { soleAccount } from "./li.js"

const acc = (key, connected) => ({ key, connected })

describe("soleAccount", () => {
  it("returns the key when exactly one account is signed in", () => {
    expect(soleAccount([acc("dgm", true)])).toBe("dgm")
    expect(soleAccount([acc("a", false), acc("dgm", true)])).toBe("dgm")
  })
  it("returns null when none or several are signed in", () => {
    expect(soleAccount([])).toBeNull()
    expect(soleAccount([acc("a", false)])).toBeNull()
    expect(soleAccount([acc("a", true), acc("b", true)])).toBeNull()
  })
})
