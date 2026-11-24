import { describe, expect, it } from "vitest"
import { changes } from "./MgrEditPanel.jsx"

const fields = [{ name: "label", type: "text" }, { name: "client_id", type: "text" }, { name: "client_secret", type: "secret" }, { name: "expires_on", type: "date" }]
const saved = { label: "Main", client_id: "123-a", client_secret: "old", expires_on: "2027-01-31" }

describe("Edit panel", () => {
  it("starts from the saved values and sends nothing until something changes", () => {
    expect(changes(fields, saved, { ...saved })).toEqual({})
    expect(changes(fields, saved, { ...saved, label: "Main " })).toEqual({})  // spaces alone are not a change
  })
  it("sends only the changed values, trimmed", () => {
    expect(changes(fields, saved, { ...saved, client_secret: " new ", label: "New" })).toEqual({ label: "New", client_secret: "new" })
  })
  it("a cleared date is sent as empty so the backend removes it", () => {
    expect(changes(fields, saved, { ...saved, expires_on: "" })).toEqual({ expires_on: "" })
  })
})
