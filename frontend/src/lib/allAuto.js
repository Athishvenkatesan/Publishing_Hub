// What the combined screen ticks for you after the AI has watched the video. Pure logic so it can be tested.
// The person's own choices always win: anything in `hand` (platforms switched by hand, accounts ticked by hand) is left alone.

// kids: the AI's "made for kids" verdict. channels: the YouTube channel suggestion ({ recommended, ranked }) or null.
// metaTargets: the Meta accounts the token can post to. Returns { off: platforms to switch off, targets: { youtube, meta: [keys] }, why: { platform: reason } }.
export function autoPlan({ kids, channels, youtubeAccounts, metaTargets = [], hand = {} }) {
  const platforms = hand.platforms || {}, accounts = hand.accounts || {}
  const off = [], targets = {}, why = {}
  if (kids && !platforms.linkedin) {
    off.push("linkedin")
    why.linkedin = "Switched off for you: this video is made for kids, which does not suit LinkedIn. Tick it if you want it there."
  }
  const ok = (channels?.recommended || []).filter((k) => youtubeAccounts.some((a) => a.key === k && a.connected))
  if (ok.length && !accounts.youtube) {
    targets.youtube = ok
    why.youtube = "Ticked from the video: " + ok.map((k) => {
      const r = (channels.ranked || []).find((x) => x.key === k)
      return `${r?.label || k}${r?.reason ? ` (${r.reason})` : ""}`
    }).join("; ") + "."
  }
  if (metaTargets.length && !accounts.meta) {
    targets.meta = metaTargets
    why.meta = "Ticked for you: every Meta account the token can post to."
  }
  return { off, targets, why }
}
