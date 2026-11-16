import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "@astryxdesign/core/reset.css"
import "@astryxdesign/core/astryx.css"
import "./dewa/theme-dewa.css"
import "./styles/themes.css"
import "./styles/app.css"
import { initTheme } from "./lib/theme.js"
import Publish from "./pages/Publish.jsx"

initTheme()
createRoot(document.getElementById("root")).render(<StrictMode><Publish /></StrictMode>)
