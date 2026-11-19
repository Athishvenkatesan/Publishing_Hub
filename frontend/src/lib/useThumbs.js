// State and calls for the thumbnail maker: pick candidates, edit the headline, re-render, hand the JPEG to the upload form.
import { useCallback, useEffect, useRef, useState } from "react"
import { ytThumbCandidates, ytThumbRender } from "./api.js"

const idle = { status: "idle", error: "", job: "", candidates: [], headlines: [], note: "", rankedBy: "", orientation: "" }

export function useThumbs(onFile) {
  const [t, setT] = useState(idle)
  const [picked, setPicked] = useState("")
  const [headline, setHeadline] = useState("")
  const [style, setStyle] = useState("band")
  const [logo, setLogo] = useState(false)
  const [enabled, setEnabled] = useState(true)
  const [preview, setPreview] = useState(null)
  const [rendering, setRendering] = useState(false)
  const [error, setError] = useState("")
  const last = useRef("")

  const clear = useCallback(() => { setT(idle); setPicked(""); setHeadline(""); setPreview(null); setEnabled(true); onFile(null) }, [onFile])

  const generate = useCallback(async (file, lang, hint, description, title, startOn = true) => {
    setT({ ...idle, status: "working" }); setPicked(""); setPreview(null); setEnabled(startOn); onFile(null)
    try {
      const d = await ytThumbCandidates(file, lang, hint, description || "", title || "")
      setT({ status: "done", error: "", job: d.job_id, candidates: d.candidates, headlines: d.headlines, note: d.note, rankedBy: d.ranked_by, orientation: d.orientation })
      setPicked(d.candidates[0].id); setHeadline(d.headlines[0] || ""); setStyle(d.style); setLogo(false)
    } catch (e) { setT({ ...idle, status: "error", error: e.message }) }
  }, [onFile])

  // Re-render whenever the choice changes (short delay while typing the headline).
  useEffect(() => {
    if (t.status !== "done" || !picked) return
    const key = JSON.stringify([t.job, picked, headline, style, logo])
    const timer = setTimeout(async () => {
      setRendering(true); setError("")
      try {
        const blob = await ytThumbRender({ job_id: t.job, frame_id: picked, headline, style, logo })
        if (last.current) URL.revokeObjectURL(last.current)
        last.current = URL.createObjectURL(blob)
        setPreview(last.current)
        if (enabled) onFile(new File([blob], "thumbnail.jpg", { type: "image/jpeg" }))
      } catch (e) { setError(e.message) } finally { setRendering(false) }
    }, key === "" ? 0 : 350)
    return () => clearTimeout(timer)
  }, [t.status, t.job, picked, headline, style, logo, enabled, onFile])

  useEffect(() => () => last.current && URL.revokeObjectURL(last.current), [])

  // Switching off removes the thumbnail from the upload. An own upload from Advanced just stops this one from overriding it.
  const toggle = useCallback((on) => { setEnabled(on); if (!on) onFile(null) }, [onFile])
  const useOwn = useCallback(() => setEnabled(false), [])

  return { ...t, picked, setPicked, headline, setHeadline, style, setStyle, logo, setLogo, enabled, toggle, useOwn, preview, rendering, error, generate, clear }
}
