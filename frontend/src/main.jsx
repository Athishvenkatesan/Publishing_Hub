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

initTheme()
const router = createHashRouter([{ path: "/", element: <Publish /> }, { path: "/meta", element: <Facebook /> }, { path: "/youtube", element: <YouTube /> }, { path: "/youtube/accounts", element: <YouTubeAccounts /> }, { path: "/youtube/studio", element: <YouTubeStudio /> }])
createRoot(document.getElementById("root")).render(<StrictMode><RouterProvider router={router} /></StrictMode>)
