// Editable text per platform <-> the payload the backend sends to Zernio.
export const emptyCopy = () => ({
  instagram: { caption: "", hashtags: "" },
  youtube: { title: "", description: "", tags: "", visibility: "public" },
})

export const fromAi = (c) => ({
  instagram: { caption: c.instagram.caption, hashtags: c.instagram.hashtags.map((h) => `#${h}`).join(" ") },
  youtube: { title: c.youtube.title, description: c.youtube.description, tags: c.youtube.tags.join(", "), visibility: "public" },
})

const list = (s) => s.split(/[,\n]/).map((x) => x.trim()).filter(Boolean)

export function toPayload(c) {
  const ig = [c.instagram.caption.trim(), c.instagram.hashtags.trim()].filter(Boolean).join("\n\n")
  return {
    instagram: { caption: ig },
    youtube: { title: c.youtube.title.trim(), caption: c.youtube.description, tags: list(c.youtube.tags),
      visibility: c.youtube.visibility },
  }
}

export const LIMITS = { igCaption: 2200, ytTitle: 100, ytDescription: 5000 }
