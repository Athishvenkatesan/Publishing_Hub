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

## Facebook screen (Meta Graph API)

Open **http://localhost:3100/#/facebook**. It uses a Meta user token from `backend/.env` (`META_ACCESS_TOKEN`), separate from Zernio.

- **Token check:** shows who the token belongs to, its permissions, the Pages it reaches, and whether it can publish to Facebook, publish to Instagram, or send WhatsApp messages. Read-only.
- **Publish:** pick a Page and a video, then publish now or schedule (10 minutes to 75 days ahead). Facebook posts have their own history table.
- **Needs:** the `pages_manage_posts`, `pages_read_engagement` and `pages_show_list` permissions, and a Page where you can create content.
- **Tokens expire:** a token from the Graph API Explorer lasts about 1 hour. When it expires the screen says so. Generate a new one, replace the value in `.env`, and restart the backend.
- **Not wired yet:** Instagram and WhatsApp through Meta are checked but cannot send from this screen.

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
