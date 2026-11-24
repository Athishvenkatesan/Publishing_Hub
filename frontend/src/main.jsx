import AllPlatforms from "./pages/AllPlatforms.jsx"
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
import MetaAccounts from "./pages/MetaAccounts.jsx"
import Publish from "./pages/Publish.jsx"
import YouTube from "./pages/YouTube.jsx"
import Accounts from "./pages/Accounts.jsx"
import PostPage from "./pages/PostPage.jsx"
import SignInDone from "./pages/SignInDone.jsx"
import { LINKEDIN, X } from "./lib/platforms.js"
import YouTubeStudio from "./pages/YouTubeStudio.jsx"

// Google or LinkedIn can send the sign-in answer to this page's own address (when that is the address the app lists). The backend is the one
// that finishes the sign-in, so hand the answer over and let it bring us back. LinkedIn states start with linkedin-.
const answer = new URLSearchParams(window.location.search)
const googleAnswer = window.location.pathname === "/" && answer.has("state") && (answer.has("code") || answer.has("error"))
if (googleAnswer) window.location.replace((answer.get("state")?.startsWith("linkedin-") ? "/api/linkedin/callback" : "/api/youtube/callback") + window.location.search)

initTheme()
const router = createHashRouter([{ path: "/", element: <Publish /> }, { path: "/meta", element: <Facebook /> }, { path: "/meta/accounts", element: <MetaAccounts /> }, { path: "/youtube", element: <YouTube /> }, { path: "/youtube/accounts", element: <Accounts key="youtube" kind="youtube" /> }, { path: "/linkedin", element: <PostPage key="linkedin" p={LINKEDIN} /> }, { path: "/linkedin/accounts", element: <Accounts key="linkedin" kind="linkedin" /> }, { path: "/linkedin/done", element: <SignInDone /> },
  { path: "/all", element: <AllPlatforms /> }, { path: "/x", element: <PostPage key="x" p={X} /> }, { path: "/x/accounts", element: <Accounts key="x" kind="x" /> }, { path: "/x/done", element: <SignInDone type="x-signin" back="/x/accounts" name="X" /> }, { path: "/youtube/studio", element: <YouTubeStudio /> }])
if (!googleAnswer) createRoot(document.getElementById("root")).render(<StrictMode><RouterProvider router={router} /></StrictMode>)
