# DGM Publishing Hub (POC)

One screen to publish a video to social media. Upload a clip, let a **local AI model** write the title, caption and hashtags, check the text, then choose **Publish now** or **Schedule** and press the button. A history table shows whether each post went out.

This is a proof of concept. It posts to **Instagram** and **YouTube** through the [Zernio](https://zernio.com) API, and the AI runs on your own laptop through [Ollama](https://ollama.com). No video or text is sent to an AI cloud.

## What it does

| Step | What happens |
|---|---|
| 1. Upload | You pick an MP4 or MOV (up to 300 MB). The AI starts by itself. |
| 2. AI analysis | A vision model looks at 6 frames from the video and describes it. A text model then writes an Instagram caption and hashtags, and a YouTube title, description and tags. You can pick English, Arabic or both, and add a line of context. |
| 3. Check the text | Every field is editable. Character limits are checked as you type (Instagram 2,200, YouTube title 100, description 5,000). Live previews show how each post will look. |
| 4. Choose the time | **Publish now**, or **Schedule** with a date and time (Asia/Dubai). Press the button. |
| 5. History | Each post and account gets a row with status, time, and a link to the post. The table refreshes every 10 seconds. |

Accounts are managed inside the app. **Manage accounts** opens a side panel where you connect or disconnect channels without opening zernio.com.

### Post statuses

`Published`, `Scheduled - not published yet`, `Publishing...`, `Failed - not published` (with the reason), `Cancelled`.

## Architecture

```
Browser (React, port 3100)
   |  /api/*  (Vite proxy)
   v
FastAPI backend (port 8100) ---- SQLite (history)
   |            |
   |            +---- Ollama (port 11434): qwen2.5vl:7b (looks), qwen2.5:7b-instruct (writes)
   |            +---- ffmpeg / ffprobe: video info and frames
   v
Zernio API ---> Instagram, YouTube
```

`backend/zernio.py` is the only file that knows Zernio's wire format. To change provider, replace that module and leave the routes alone.

### Project layout

```
POC/
  package.json            convenience scripts (install:all, dev, dev:backend, test)
  PLAN.md  PROJECT.md  CONVENTIONS.md
  backend/
    app.py                thin app: logging, startup, routers, /healthz, /readyz
    config.py             settings read from backend/.env
    db.py  models.py      SQLite + the Publication table
    zernio.py             Zernio client (accounts, media upload, posts, connect)
    status.py             maps Zernio statuses to ours
    frames.py             ffprobe + ffmpeg frame extraction
    analyzer.py           local AI: describe the video, write the text
    routes/               accounts.py, posts.py, analyze.py
    tests/                pytest tests (Zernio is mocked)
  frontend/
    src/pages/Publish.jsx the one page
    src/components/       Hero, UploadStep, CopyEditor, WhenStep, PostPreview,
                          HistoryTable, AccountsPanel, PublishForm
    src/lib/              api, copy, time, theme helpers
    src/dewa/             DEWA theme (Astryx design system)
```

## Requirements

- **Python** 3.12 or newer
- **Node.js** 20 or newer
- **ffmpeg** (includes `ffprobe`): `brew install ffmpeg`
- **Ollama** with two models (about 11 GB of disk and several GB of free memory)
- A **Zernio account** and API key, with Instagram and/or YouTube connected
- An Instagram **professional** (Business or Creator) account. Personal Instagram accounts cannot publish through the API.

## Setup

### 1. Install the dependencies

```bash
npm run install:all
```

This runs `npm install` for the frontend, creates `backend/.venv`, and installs the Python packages.

### 2. Install the local AI models

```bash
ollama pull qwen2.5vl:7b
ollama pull qwen2.5:7b-instruct
```

The first download is large (about 6 GB and 4.7 GB). Make sure Ollama is running (`ollama serve`, or the Ollama app).

### 3. Add your Zernio key

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and set `ZERNIO_API_KEY`. Get the key from the Zernio dashboard (API keys). **Never commit `.env`.** It is already in `.gitignore`.

| Variable | Default | Meaning |
|---|---|---|
| `ZERNIO_API_KEY` | (empty) | Your Zernio API key. Required. |
| `ZERNIO_BASE_URL` | `https://zernio.com/api/v1` | Zernio API address. |
| `DEFAULT_TIMEZONE` | `Asia/Dubai` | Time zone for scheduled posts. |
| `PUBLIC_BASE_URL` | (empty) | Not used by the current flow. |
| `META_ACCESS_TOKEN` | (empty) | Meta Graph API user token for the Facebook screen. |
| `META_GRAPH_VERSION` | `v21.0` | Graph API version. |
| `YOUTUBE_ACCOUNTS` | (empty) | Comma-separated keys of the YouTube accounts, e.g. `first,second`. |
| `YOUTUBE_<KEY>_LABEL` / `_CLIENT_ID` / `_CLIENT_SECRET` | (empty) | One set per account: its name on screen and its own Google OAuth client. See `.env.example`. |
| `THREADS_ACCESS_TOKEN` | (empty) | Optional. Threads has its own token; a Facebook token does not work for Threads. |

You can also override the AI settings in `.env`: `OLLAMA_URL`, `VISION_MODEL`, `TEXT_MODEL`, `ANALYZE_FRAMES` (default 6) and `MAX_VIDEO_MB` (default 300).

### 4. Connect your accounts

Start the app (next section), click **Manage accounts**, and press **Connect Instagram** or **Connect YouTube**. You sign in on the platform's own page and come back to the app. Accounts you connected earlier on zernio.com also appear.

## Run it

You need two terminals.

```bash
# Terminal 1: backend (port 8100)
npm run dev:backend

# Terminal 2: frontend (port 3100)
npm run dev
```

Open **http://localhost:3100**.

Check the backend any time: http://localhost:8100/healthz should return `{"ok":true}`.

If the page says "Accounts not loaded" or "Local AI is not ready", the backend or Ollama is not running. Start it and the page recovers by itself within 10 seconds.

## Using it

1. Drop a video into **Upload the video**. The AI analysis starts and takes roughly 30 to 60 seconds.
2. Read **What the AI found** and the text under **Check the text**. Edit anything you like. Untick an account to skip it.
3. Under **Choose the time**, pick **Publish now** or **Schedule** and set the date and time.
4. Press **Publish** (or **Schedule post**). Watch the **History** table below.

For YouTube you can choose **Public**, **Unlisted** or **Private**.

## Insta - Face - Threads screen (Meta Graph API)

Open **http://localhost:3100/#/meta**. It uses a Meta user token from `backend/.env` (`META_ACCESS_TOKEN`), separate from Zernio.

- **Token check:** shows who the token belongs to, its permissions, the Pages it reaches, and whether it can publish to Facebook, publish to Instagram, or send WhatsApp messages. Read-only.
- **Publish:** pick a Page and a video, then publish now or schedule (10 minutes to 75 days ahead). Facebook posts have their own history table.
- **Needs:** the `pages_manage_posts`, `pages_read_engagement` and `pages_show_list` permissions, and a Page where you can create content.
- **Tokens expire:** a token from the Graph API Explorer lasts about 1 hour. When it expires the screen says so. Generate a new one, replace the value in `.env`, and restart the backend.
- **Not wired yet:** Instagram and WhatsApp through Meta are checked but cannot send from this screen.

## YouTube screen (your own Google apps, several accounts)

Open **http://localhost:3100/#/youtube**. It signs in with your Google OAuth client (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` in `backend/.env`) and uploads straight to your channel.

- **Google setup (once):** in Google Cloud, enable **YouTube Data API v3**. In **Credentials**, edit the OAuth client and add `http://localhost:8100/api/youtube/callback` under **Authorized redirect URIs**, and `http://localhost:3100` under **Authorized JavaScript origins**. On the **OAuth consent screen**, add your Google account under **Test users**.
- **Several accounts:** each account has its own Google OAuth client and its own sign-in, listed in `backend/.env` (add a key to `YOUTUBE_ACCOUNTS` plus its `YOUTUBE_<KEY>_LABEL`, `_CLIENT_ID` and `_CLIENT_SECRET`). The screen shows a switcher; uploads, thumbnails, the history Action menu and Studio all work on the account you pick, and every history row shows which account it belongs to. A client of type **Desktop app** needs no redirect address; a **Web application** client needs `http://localhost:8100/api/youtube/callback` added under Authorized redirect URIs. Each account's sign-in is saved in `backend/youtube_tokens/<key>.json` (git-ignored). The older single `YOUTUBE_CLIENT_ID`/`YOUTUBE_CLIENT_SECRET` pair still works as one account called `main`.
- **Connect:** press **Connect YouTube**, sign in, and allow upload access. The refresh token is saved in `backend/youtube_token.json` (git-ignored).
- **Upload:** title, description, tags, visibility, then **Publish now** or **Schedule**. A scheduled video uploads as private and YouTube makes it public at the set time.
- **AI details (same idea as the Instagram + YouTube screen):** choose a video, and the local model watches it and writes 3 title options, a structured description (summary, key points, call to action, hashtags), up to 15 tags, a suggested category with a reason, 2 thumbnail ideas, and whether it posts as a Short. Everything is editable. Needs Ollama running (`brew services start ollama`).
- **Advanced options (collapsed):** category, video language, license, made for kids, AI-generated content disclosure, allow embedding, show view and like counts, notify subscribers, and a custom thumbnail (JPG or PNG up to 2 MB; the channel must be phone-verified). A thumbnail problem is shown as a warning and never cancels the upload.
- **Thumbnail maker:** after the analysis, the local model picks the best frames and writes headlines, and the app builds three 1280x720 thumbnails from your real video (a vertical video sits on a blurred copy of itself). You can pick another frame, edit the headline (English or Arabic), choose Green strip, Dark overlay or No text, and add the DEWA logo. A "how it will look" card shows it beside the title. It works without the AI too (frames ordered by sharpness, no headline). The chosen thumbnail is added after YouTube finishes processing the video, which Shorts need. If it cannot be added, the history row says so and the upload is unaffected. **YouTube only allows custom thumbnails on phone-verified channels.** The screen checks this: on an unverified channel it shows a warning with a verify link and does not send the thumbnail by default (you can still download the JPG and set it in YouTube Studio later).
- **AI ticks the two advanced boxes, and suggests channels:** after the analysis, **Made for kids** and **Contains AI-generated or altered content** are ticked automatically when there is a reason, and the reason is shown under the box (the Advanced section opens itself). The AI-content box is ticked if the file's own metadata or tags show an AI label or tool (for example C2PA, `trainedAlgorithmicMedia`, Sora, Veo, Runway), if your context note says so, or if the vision model thinks it looks AI-generated with medium or high confidence. The kids box is ticked if your note mentions children, or the vision model judges it made for children (children merely appearing does not count). Both lean towards ticking, because leaving them off by mistake is the risky error, and no sign found does not prove a video is not AI. You can always change them, and the AI never overrides a box you already changed. The AI also **suggests channels** from each channel's name, description, keywords and kids setting: a kids video goes to kids channels, any other video stays off them.
- **Channel dropdown:** the **Post to** control is a dropdown with a tick box per channel (name, handle, AI suggests, Kids channel, Not verified badges), a Connect button next to signed-out ones, **+ Add another channel** (opens the add-account panel) and Manage accounts. Selected channels also show as chips. A warning appears if the video is made for kids but a selected channel is not a kids channel, or the other way round.
- **Post to several accounts at once:** when two or more accounts are signed in, the publish step shows a **Post to** list. Tick as many as you want and press one button: the same video, title, description, tags, advanced options, thumbnail and schedule go to every ticked account **in parallel**, each with its own sign-in, so a scheduled video goes public at the same moment everywhere. Each account gets its own history row (rows from one submission share a group). If one account fails, the others still go out and the message lists who succeeded and who failed. Accounts that share a Google app also share that Google project's quota. Each channel needs its own phone verification for custom thumbnails.
- **Which return address is used:** after sign-in Google sends you back to an address the client must list. The app tries `http://localhost:8100/api/youtube/callback` first. If the client does not list it but does list `http://localhost:3100` (the web page's own address, a common slip: the JavaScript origin pasted into the redirect list), the app uses that one instead: the page hands Google's answer to the backend (`main.jsx`), which finishes the sign-in and brings you back. A **Desktop app** client accepts either without any setting. If a client lists neither, Connect shows the two addresses and what to do.
- **Connect is checked first:** pressing Connect asks Google whether it will accept the sign-in. If not (for example a Web-type client that does not list the redirect address), you stay in the app and see exactly what to fix, instead of landing on Google's error page.
- **Accounts manager** (`#/youtube/accounts`, or Manage accounts on the YouTube screen): add an account by pasting a Google client ID and secret (saved only in `backend/youtube_accounts.json`, git-ignored, mode 600, and never sent back to the browser), or add another channel on a Google app you already added. Each account card shows whether it is connected and a live **checklist**: Google app saved, Google accepts the sign-in, signed in, channel found, channel phone-verified, permission to edit and delete videos, permission to read reports and the YouTube Analytics API. Each to-do has the button that fixes it. A step-by-step guide for Google Cloud sits beside the list with copy buttons for the redirect address and origin. Accounts set in `.env` are shown read-only.
- **Studio management** (`#/youtube/studio`, or the Studio management button on the channel card): for the chosen account. **Overview** (channel profile, totals, last-28-day numbers, feature status, shortcuts into YouTube Studio), **Content** (every video with visibility, schedule, length, views, likes, comments, search, filter and CSV), **Reports** (views, watch time, net subscribers, likes, comments, shares and average view duration against the previous period, one metric over time, top videos, traffic sources, countries, devices, age and gender, each with a CSV; period presets and print/PDF), **Playlists**, and **Access** (the permissions this app holds, read live from Google, with buttons to add the reports or manage-videos permission, what YouTube does not share, and YouTube's channel roles). Reports need the YouTube Analytics API enabled in the Google project and the reports permission.
- **Action column:** each row in the YouTube history has a three-dot menu: Open on YouTube, Copy link, Edit title/description/tags, Reschedule and Cancel schedule (scheduled videos only), Set visibility (Public, Unlisted, Private), Remove from this list (the video on YouTube is untouched), and Delete from YouTube (permanent, confirmed in the side panel). Each edit costs 50 YouTube quota units.
- **Fonts:** thumbnails use Figtree and Noto Sans Arabic from `backend/assets/fonts` (SIL Open Font License).
- **Limits:** a Google project in Testing mode signs you out after 7 days. A new project's uploads may stay private until it passes YouTube's audit; the history says so when that happens.

## LinkedIn screen (your own LinkedIn apps, several accounts)

Open **http://localhost:3100/#/linkedin** (the **LinkedIn** link in the top bar). It works like the YouTube screen: add accounts on screen, sign each in, and post one video to one or several accounts at once. Posting is **as the signed-in person's profile**.

- **LinkedIn setup (once per app):** in the [LinkedIn Developer portal](https://www.linkedin.com/developers/apps) create an app (it must be attached to a LinkedIn Page you manage). On the **Products** tab add **Share on LinkedIn** and **Sign In with LinkedIn using OpenID Connect**. On the **Auth** tab add `http://localhost:8100/api/linkedin/callback` under **Authorized redirect URLs for your app** and press Update, then copy the **Client ID** and **Primary Client Secret**. LinkedIn has no test-user list: the member who signs in just allows the app.
- **Two ways to sign in.** (1) **Connect** opens LinkedIn in a popup window that closes itself when done (the normal sign-in): needs the redirect address added under Authorized redirect URLs for your app. (2) **Connect with a token** (no redirect URL at all): in the Developer portal open the OAuth token generator (Docs and tools), pick your app, tick `openid`, `profile`, `email` and `w_member_social`, approve, copy the token and paste it on the account's card. The app asks LinkedIn (token introspection, with the app's own client ID and secret) whether the token is live, belongs to this app and carries those permissions, then saves it. Either way the app's Auth tab must show permissions: if it says **No permissions added**, add the two products first (Products tab). A pasted token lasts about 60 days, like a normal sign-in.
- **Accounts manager** (`#/linkedin/accounts`): the same screen as YouTube's. Add an account by pasting the client ID and secret (saved only in `backend/linkedin_accounts.json`, git-ignored, mode 600, never sent back to the browser) or add a second person on an app you already added. Each card has a live checklist: app saved, LinkedIn accepts the sign-in (it asks LinkedIn first, so you see what to fix instead of LinkedIn's error page), signed in (who, and days left), permission to post. Sign-ins are saved in `backend/linkedin_tokens/<key>.json` (git-ignored).
- **Post:** choose an MP4 (3 seconds to 30 minutes, up to 300 MB). The local model watches it and writes three opening lines to choose from, the post text with 3 to 5 hashtags and a video title (all editable, up to 3000 characters). Choose **Anyone** or **Connections only**, pick the accounts in the **Post to** list (nothing is ticked for you) and press Post. Characters LinkedIn treats as formatting, such as ( ) @ _, are sent as plain text so they never cut the post short; `#hashtags` stay hashtags.
- **History:** a video posted to several accounts is one row listing each account. The three-dot menu asks which account first, then: Open on LinkedIn, Copy link, Edit the post text, Remove from this list, Delete from LinkedIn.
- **Limits (LinkedIn's rules, not the app's):** a sign-in lasts **60 days** and cannot be renewed in the background (press Connect again; it is quick while you are signed in to LinkedIn). There is **no scheduled posting** in LinkedIn's public API, so every post goes out now. Posting as a **company page** needs LinkedIn's approval for the Community Management API and is not built. Reading posts back, and any analytics, are not available to a normal app, so the history is what this app sent and shows no views or likes. Each member may make about 150 API requests a day (a video uses several).
- **Tech:** Posts API (`/rest/posts`) with the `Linkedin-Version` header (`LINKEDIN_VERSION`, default `202606`), Videos API for the upload (initialize, 4 MB parts, finalize), OpenID Connect for who is signed in. Not yet verified against the real service: **no post has been made**. The sign-in check and the checklist were run against LinkedIn's real sign-in page.

## X screen (your own X apps, several accounts)

Open **http://localhost:3100/#/x** (the **X** link in the top bar). Same layout as the LinkedIn screen: add accounts on screen, sign each in, and post one video to one or several X accounts at once.

- **X setup (once per app):** in the X Developer Console create a project and an app, and add credits (X charges per request: about $0.015 per post; there is no free posting tier). Under **User authentication settings**: App permissions **Read and write**, Type of App **Web App, Automated App or Bot**, Callback URI / Redirect URL **`http://127.0.0.1:8100/api/x/callback`** (X does not accept `localhost`), Website URL any address you own. On **Keys and tokens** copy the **OAuth 2.0 Client ID and Client Secret**. The API Key, API Key Secret and the Access Token on that page are OAuth 1.0a values and are not used.
- **Accounts manager** (`#/x/accounts`): add the Client ID and Secret (saved only in `backend/x_accounts.json`, git-ignored, mode 600). Connect opens X in a popup (OAuth 2.0 with PKCE). The sign-in asks for `tweet.read tweet.write users.read media.write offline.access`; `offline.access` gives a refresh token, so the 2-hour access token renews itself and you do not sign in again. Sign-ins are saved in `backend/x_tokens/<key>.json` (git-ignored). X's sign-in page cannot be checked in advance, so the checklist marks the callback as done after the first good sign-in, then checks the permissions.
- **Post:** an MP4 or MOV; the local model writes three short posts (up to 240 characters with 1 or 2 hashtags) to pick from; **Who can reply** (Everyone, People you follow, Only mentioned); tick the accounts; Post. The upload uses the v2 chunked media upload (initialize, 4 MB parts, finalize, wait for processing). 280 characters on a normal account; longer only for Premium.
- **History:** grouped per video like the other screens; Open on X, Copy link, Remove from this list, Delete from X. X's API has no editing and no scheduled posts.
- **Not verified against the real service:** no X account has been added or signed in yet; everything is tested with a mocked X.

## API

All routes are under `/api`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/accounts` | Connected accounts (platform, name, status, followers) |
| `POST` | `/accounts/connect` | Returns a Zernio sign-in link for a platform |
| `DELETE` | `/accounts/{id}` | Disconnect an account |
| `GET` | `/analyze/status` | Is the local AI ready? |
| `POST` | `/analyze` | Upload a video, get description, title, caption, hashtags |
| `POST` | `/posts` | Publish now or schedule (multipart: file, texts, account_ids, mode, scheduled_at, tz) |
| `GET` | `/posts` | History, refreshed from Zernio |
| `GET` | `/facebook/check` | Check the Meta token: user, permissions, Pages, capabilities |
| `POST` | `/facebook/posts` | Publish a video to a Facebook Page, now or scheduled |
| `GET` | `/facebook/posts` | Facebook history, refreshed from Meta |
| `GET` | `/youtube/status` | Is the Google app set, is a channel connected |
| `GET` | `/youtube/connect` | Google sign-in link |
| `POST` | `/analyze/youtube` | Upload a video, get the full YouTube package (titles, description, tags, category, thumbnail ideas) |
| `GET` | `/youtube/manager/accounts` | Accounts with status (no secrets), the setup guide |
| `POST` | `/youtube/manager/accounts` | Add an account (client ID and secret, or reuse another account's Google app) |
| `PATCH` / `DELETE` | `/youtube/manager/accounts/{key}` | Rename or remove an account added on screen |
| `GET` | `/youtube/manager/accounts/{key}/check` | Checklist of what works and what is missing |
| `GET` | `/youtube/studio/{overview,videos,playlists,access,reports}` | Studio data for the chosen account (`?account=`) |
| `GET` | `/youtube/studio/{videos,reports}.csv` | CSV downloads |
| `POST` | `/thumbnails/candidates` | Three thumbnail options from a video (AI-ranked frames and headlines) |
| `POST` | `/thumbnails/render` | Re-render one candidate with a new headline, style or logo (returns a JPEG) |
| `GET` | `/youtube/channels/profiles` | Name, handle, description, kids and verified status of each signed-in channel |
| `POST` | `/youtube/channels/suggest` | Which channels fit a video (AI, with a word-match fallback) |
| `POST` | `/youtube/posts/multi` | Upload the same video to several accounts at once (`accounts` repeated) |
| `POST` | `/youtube/posts` | Upload a video to your channel, now or scheduled |
| `GET` | `/youtube/posts/{id}/details` | Current title, description, tags, visibility of an upload |
| `PATCH` | `/youtube/posts/{id}` | Edit details, change visibility, reschedule or cancel the schedule |
| `DELETE` | `/youtube/posts/{id}` | Delete the video on YouTube and remove the row |
| `DELETE` | `/youtube/posts/{id}/local` | Remove the row from the list only |
| `GET` | `/youtube/posts` | YouTube history, refreshed from YouTube |
| `GET` | `/linkedin/accounts`, `/linkedin/status`, `/linkedin/channels/profiles` | LinkedIn accounts and sign-in state (`?account=`) |
| `GET` | `/linkedin/connect`, `/linkedin/callback` | LinkedIn sign-in link (checked first) and its return address |
| `POST` | `/linkedin/token` | Sign in with a token from the portal's token generator (no redirect URL) |
| `POST` | `/linkedin/posts/multi` | Post one video to several LinkedIn accounts at once (`accounts` repeated) |
| `GET` | `/linkedin/posts` | LinkedIn history |
| `PATCH` / `DELETE` | `/linkedin/posts/{id}` | Edit the text, or delete on LinkedIn and remove the row |
| `DELETE` | `/linkedin/posts/{id}/local` | Remove the row from the list only |
| `GET` `POST` `PATCH` `DELETE` | `/linkedin/manager/accounts[...]` | The accounts manager (same shape as YouTube's), plus `/{key}/check` |
| `GET` | `/x/accounts`, `/x/channels/profiles`, `/x/connect`, `/x/callback` | X accounts, sign-in link (PKCE) and its return address |
| `POST` | `/x/posts/multi` | Post one video to several X accounts at once |
| `GET` / `DELETE` | `/x/posts`, `/x/posts/{id}`, `/x/posts/{id}/local` | X history, delete on X, remove from the list |
| `GET` `POST` `PATCH` `DELETE` | `/x/manager/accounts[...]` | The X accounts manager, plus `/{key}/check` |
| `POST` | `/analyze/x` | Upload a video, get three short posts for X |
| `POST` | `/analyze/linkedin` | Upload a video, get opening lines, the post text with hashtags and a title |

Outside `/api`: `GET /healthz` (alive) and `GET /readyz` (ready).

## Tests

```bash
npm run test
```

Runs the backend tests with Zernio and Meta mocked: publish now, schedule, failure, text rules, past-time and bad-file rejection, connect and disconnect, and the AI analysis. No real post is made.

## Things to know

- **Scheduled Instagram posts go out at the set time even if your laptop is off.** Zernio holds them and publishes at that time. Scheduling is done by Zernio, not by this app.
- **YouTube does not schedule the same way.** Through Zernio, a scheduled YouTube upload goes live immediately. To hold a video back, set its visibility to Private or Unlisted.
- **Free plan limit:** Zernio's free plan allows 2 connected accounts. Connecting a third returns an error that the panel shows.
- **Time zone:** times are shown in Asia/Dubai and stored in UTC.
- **AI limits:** the model sees 6 still frames and does not listen to the audio. Arabic output quality is not yet verified. Always read the text before publishing.
- **Statuses** refresh when the history is read (every 10 seconds), not by webhook.
- **Not built yet:** retry and cancel buttons, withdrawing a published post, sign-in, approval flow, metrics.
- **Instagram tokens expire** (about 60 days). Reconnect from **Manage accounts** if an account shows "Reconnect".

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| "Local AI is not ready" or 503 on analyse | Ollama is not running, or a model is missing. Run `ollama serve` and the two `ollama pull` commands. |
| "Model ... is not installed" | Run the `ollama pull` command shown in the message. |
| "Accounts not loaded" | The backend is down. Run `npm run dev:backend`. |
| `npm run dev` fails | Run it from the `POC` folder, after `npm run install:all`. |
| Analyse takes very long the first time | The model is loading into memory. Later runs are faster. |
| Instagram post fails | The account must be a professional account, and the video must meet Instagram's Reel rules. |
| Zernio 402 when connecting | Free plan limit of 2 accounts. Disconnect one or add a payment method on Zernio. |

## Security

- Keep `backend/.env` private. If a key was ever shared in chat or committed, rotate it on the Zernio dashboard.
- The POC has no sign-in. Run it only on your own machine.

## Status and next steps

Proof of concept. See [PROJECT.md](PROJECT.md) for the current state and [PLAN.md](PLAN.md) for the original plan. The vendor comparison and pricing analysis for the full hub is a separate PDF that is not part of this repository.
