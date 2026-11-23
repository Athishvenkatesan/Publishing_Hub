// Posting one video to several platforms from the combined screen. Pure logic (no React) so it can be tested.
// Platforms run one after another, in the order given; one failing never stops the next.

export async function publishAll(file, jobs) {
  const results = []
  for (const j of jobs) {
    try {
      const d = await j.publish(j.toForm(file, j.form, j.accounts))
      results.push({ kind: j.kind, name: j.name, items: d.items || [], errors: d.errors || [], warnings: d.warnings || [], error: "" })
    } catch (e) {
      results.push({ kind: j.kind, name: j.name, items: [], errors: [], warnings: [], error: e.message })
    }
  }
  return results
}

export const posted = (r) => r.items.length > 0
export const failedAll = (r) => !posted(r)

// The one banner after posting: which platforms went live, which did not, and why.
export function summarise(results) {
  const ok = results.filter(posted), bad = results.filter(failedAll)
  const partial = results.filter((r) => posted(r) && r.errors.length)
  const lines = [
    ...ok.map((r) => `${r.name}: ${r.items.map((i) => i.account_name).join(" and ")}`),
    ...results.flatMap((r) => r.errors.map((e) => `${r.name} - ${e.label}: ${e.error}`)),
    ...bad.filter((r) => r.error).map((r) => `${r.name}: ${r.error}`),
    ...results.flatMap((r) => r.warnings),
  ]
  if (!ok.length) return { status: "error", title: "Nothing was posted", description: lines.join(" | ") }
  const all = !bad.length && !partial.length
  return { status: all ? "success" : "warning", title: all ? `Posted to ${ok.length} ${ok.length === 1 ? "platform" : "platforms"}` : "Posted, but not everywhere",
    description: all ? lines.filter(Boolean).join(" | ") : lines.join(" | ") }
}

// Platforms that went live are switched off afterwards, so pressing Post again retries only the ones that failed.
export const retryOnly = (results) => results.filter((r) => posted(r) && !r.errors.length).map((r) => r.kind)
