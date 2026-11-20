import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { RouterProvider, createHashRouter } from "react-router"
import "@astryxdesign/core/reset.css"
import "@astryxdesign/core/astryx.css"
import "./dewa/theme-dewa.css"
import "./styles/themes.css"
import "./styles/app.css"
import { initTheme } from "./lib/theme.js"
import Facebook from "./pages/Facebook.jsx"
import Publish from "./pages/Publish.jsx"
import YouTube from "./pages/YouTube.jsx"
import YouTubeAccounts from "./pages/YouTubeAccounts.jsx"
import YouTubeStudio from "./pages/YouTubeStudio.jsx"

// Google can send the sign-in answer to this page's own address (when that is the address the client lists, which is a common
// way to register a Web client). The backend is the one that finishes the sign-in, so hand the answer over and let it bring us back.
const answer = new URLSearchParams(window.location.search)
const googleAnswer = window.location.pathname === "/" && answer.has("state") && (answer.has("code") || answer.has("error"))
if (googleAnswer) window.location.replace("/api/youtube/callback" + window.location.search)

initTheme()
const router = createHashRouter([{ path: "/", element: <Publish /> }, { path: "/meta", element: <Facebook /> }, { path: "/youtube", element: <YouTube /> }, { path: "/youtube/accounts", element: <YouTubeAccounts /> }, { path: "/youtube/studio", element: <YouTubeStudio /> }])
if (!googleAnswer) createRoot(document.getElementById("root")).render(<StrictMode><RouterProvider router={router} /></StrictMode>)
