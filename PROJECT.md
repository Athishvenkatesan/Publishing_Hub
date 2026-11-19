---
goal: Prove one screen can upload a video and publish it now or at a set time to connected social accounts
domain: DGM publishing hub
audience: DGM team
status: building
---
# DGM Publishing Hub POC

## Current State (16 Nov 2026)
- Screen works: upload clip, caption, pick accounts, publish now or schedule (Asia/Dubai), history table with status and post link.
- Provider: Zernio. Connected accounts: Instagram `aivideo.3321`, YouTube `athishvenkatesan9293`.
- Local AI (Ollama: qwen2.5vl:7b + qwen2.5:7b-instruct) analyses the video and writes title, caption and hashtags per platform. Tested on a sample clip.
- Backend tests pass (8). Frontend builds. Posts have been published through the app (history shows them).
- Full setup and usage: see README.md.

## Run
Backend: `cd backend && .venv/bin/uvicorn app:app --port 8100`
Frontend: `cd frontend && npm run dev` then open http://localhost:3100
Tests: `cd backend && .venv/bin/pytest -q`
Key lives in `backend/.env` (ZERNIO_API_KEY). Never commit it.

## Deviation note
Not scaffolded with `dak init`: this is a single-screen POC. SQLite instead of Postgres, no Docker, no auth, no /journey pages. Revisit if the POC becomes the real hub.

## Known limits
- Statuses refresh when the history is read (every 10 s), not by webhook.
- No withdraw, retry or cancel button yet.
- A scheduled YouTube upload goes live immediately via Zernio; use Private or Unlisted to hold it back.
- Instagram needs a professional account; YouTube uploads are quota-limited.

## 2026-11-13 - in-app account management and new layout
- Accounts are managed inside the app (slide-in panel): `GET /api/accounts`, `POST /api/accounts/connect` (Zernio OAuth link, returns to the app), `DELETE /api/accounts/{id}`. No need to open zernio.com.
- New layout: green hero band with live counts, three fluid columns (upload, text, time + live post previews), history below.
- Zernio free plan allows 2 connected accounts; connecting a third returns a 402 message that the panel shows.

## 2026-11-18 - Facebook screen (Meta Graph API)
- New screen `#/meta` ("Insta - Face - Threads") (nav bar links both screens): checks the Meta token (user, permissions, Pages, what it can do for Facebook / Instagram / WhatsApp), publishes a video to a Facebook Page now or scheduled (10 minutes to 75 days ahead), own history.
- Backend: `meta.py` (only Meta-aware module), `routes/facebook.py`, token in `backend/.env` as `META_ACCESS_TOKEN` (never commit). Page tokens stay on the server.
- Graph API Explorer tokens last about 1 hour. When one expires the screen says so. For longer use, exchange it for a long-lived token (needs the app secret).
- Facebook rows are kept out of the Instagram + YouTube history. Instagram and WhatsApp via Meta are checked but not wired yet.
- Tests: 12 pass (4 new, Meta mocked). No real Facebook post has been made.

## 2026-11-19 - Photo posting on the Insta - Face - Threads screen
- Facebook photo posting: `POST /api/facebook/photos` (JPG or PNG up to 10 MB, caption, now or scheduled). Same `pages_manage_posts` permission as video.
- Screen renamed "Insta - Face - Threads" (`#/meta`), with a card per channel showing what the token can do. Threads needs its own token (`THREADS_ACCESS_TOKEN`).
- Page token is now read from the Page list (works without `pages_read_engagement`).
- Scheduled photos show SCHEDULED until their time passes, then PUBLISHED once Facebook returns the photo link (untested against live Facebook).
- Tests: 14 pass (Meta mocked). Nothing has been posted to Facebook yet: the token still lacks `pages_manage_posts`.

## 2026-11-19 - YouTube screen (direct Google OAuth)
- New screen `#/youtube`: Google sign-in (offline access), channel card, resumable upload to YouTube Data API v3, real scheduling (`publishAt`, uploaded private), own history (platform `youtube-direct`, kept out of the Zernio history).
- Backend: `youtube.py` (only Google-aware module), `routes/youtube.py`; refresh token in `backend/youtube_token.json` (git-ignored). Credentials in `backend/.env`.
- Replaced the Astryx file button with a native picker (`FilePick.jsx`): the old one opened the dialog by a scripted click that fired twice.
- Needs in Google Cloud: YouTube Data API v3 enabled, redirect URI `http://localhost:8100/api/youtube/callback`, your account as a test user.
- Tests: 20 pass (Google mocked). Not yet signed in or uploaded against real Google.

## 2026-11-19 - YouTube screen: AI details and advanced options
- Same flow as Instagram + YouTube: upload, local AI analysis, review, publish. New `POST /api/analyze/youtube` (`analyzer.write_youtube`): 3 titles, structured description, tags, hashtags, category (+reason, guardrail against over-picking Nonprofits & Activism), thumbnail ideas (fallback from key points), Short vs video.
- Advanced options on upload: category, language, license, made for kids, AI-content disclosure, embeddable, public stats, notify subscribers, custom thumbnail (separate `thumbnails.set` call, failure = warning).
- Screen split into `YtStudio` + `YtUpload`, `YtReview`, `YtAdvanced`, `YtWhen`; `AiFound` shared with the first screen.
- Tests: 27 pass. Real analysis run on a sample video (44 s). Channel connected and a test upload appears in history. Not yet verified: a real upload with advanced options, and a real custom thumbnail.

## 2026-11-19 - YouTube history: Action column
- "Post" column replaced by "Action" with a three-dot menu per row (Astryx MoreMenu): open, copy link, edit details, reschedule / cancel schedule (scheduled rows), visibility, remove from list, delete from YouTube.
- Edits read the video first and send the full snippet/status back (YouTube erases omitted fields). Edit, reschedule and delete use a slide-in panel, no popups. Errors show under the video title.
- Backend: `GET/PATCH/DELETE /api/youtube/posts/{id}`, `DELETE .../local`. Tests: 31 pass (Google mocked).
- Not yet run against a real video: save an edit, reschedule, cancel schedule, delete. The menu and the edit panel's read of the real video were checked in the browser.

## 2026-11-19 - YouTube thumbnail maker (Option A: real frame + headline)
- Backend: `thumb_frames.py` (12 frames, drop dark, sharpest and spread apart), `thumb_ai.py` (vision model ranks frames, text model writes headlines; both optional), `thumb_render.py` (Pillow, 1280x720 JPEG under 2 MB, blurred-background for vertical video, Green strip / Dark overlay / No text, optional logo, Arabic shaping + bidi with measured letter heights), `thumb_jobs.py` (temp working folders, 1 h), `routes/thumbnails.py`.
- Phase 0: custom thumbnails now wait for YouTube processing (`yt_thumbnail.py`, polls `processingDetails`, resumes after a restart). The old code set it right after upload, which Shorts may ignore.
- Frontend: `YtThumbs` (preview, 3 candidates, headline, style, logo, use-on/off, download), `YtPreviewCard`, `useThumbs` hook. Output is attached to the existing `thumbnail` field, so publishing is unchanged.
- Real run on the 15 s vertical sample: analysis 47 s, thumbnails ready at 85 s total. 39 backend tests pass.
- Not verified: a real thumbnail set on a real video or Short, and whether YouTube shows custom thumbnails for Shorts. Not built: AI-generated images (Option B), reuse as the Instagram Reel cover.
- Added: Pillow, arabic-reshaper, python-bidi; fonts Figtree and Noto Sans Arabic (OFL), DEWA logo copy in `backend/assets`.

## 2026-11-19 - Thumbnail refused: channel not verified
- Root cause: YouTube returned 403 "doesn't have permissions to upload and set custom video thumbnails". The channel was created the same day and reports `longUploadsStatus: eligible` (not `allowed`), i.e. not phone-verified. It is a channel limit, not a missing OAuth scope (`youtube.upload` is accepted by thumbnails.set).
- Fix: `youtube.channel()` now returns `long_uploads`, `verified` and `verify_url`. The YouTube screen warns before upload and defaults "Use this thumbnail on YouTube" to off while unverified. The refusal note in history now says what to do. Tests: 47 pass.
- Also found: `videos.update` and `videos.delete` do NOT accept the `youtube.upload` scope, so the history Action menu's edit, visibility, reschedule and delete need the broader `youtube` scope. Sign-in can now request it (`/api/youtube/connect?manage=true`); a refusal shows a plain message. Not yet tested against the real channel.
- Studio management (in progress): backend `yt_studio.py`, `routes/yt_studio.py` (overview, videos, playlists, access, reports, CSV) with 6 tests; chart components built. The Studio screen and tabs are not built yet.

## 2026-11-19 - Several YouTube accounts
- Accounts are listed in `backend/.env` (`YOUTUBE_ACCOUNTS=a,b` plus `YOUTUBE_<KEY>_LABEL/_CLIENT_ID/_CLIENT_SECRET`). Added: `dgmgenmedia` (existing Desktop client) and `athish0204` (new client, Web type).
- Backend: `yt_accounts.py` (loads accounts, one refresh-token file per account in `youtube_tokens/`, a per-request choice via `?account=`), every YouTube route and the Studio routes take `?account=`. A Publication row stores its account in `account_id` (older rows fall back to the first account) so refresh, the Action menu and the delayed thumbnail use the right sign-in. Pending thumbnail files are named `<account>~<video>`.
- The existing sign-in was moved to `youtube_tokens/dgmgenmedia.json`, so that account stayed connected.
- Frontend: `YtAccounts` switcher in the channel step (choice remembered in the browser), account shown in history rows.
- New account status: its client secret is valid, but Google rejects our redirect address (`redirect_uri_mismatch`), so it is not signed in yet. Tests: 52 pass.

## 2026-11-19 - Studio management and Accounts manager
- Studio management screen built (`#/youtube/studio`): Overview, Content, Reports, Playlists, Access. Charts are plain SVG following the single-colour rules (one accent, ranked bars, stat tiles with change vs previous period, crosshair tooltip, table view, CSV). Run against the real channel: overview, 5 videos, playlists and permissions read correctly; Reports correctly says the YouTube Analytics API is not switched on in that Google project.
- Accounts manager built (`#/youtube/accounts`): add an account by client ID and secret (`youtube_accounts.json`, git-ignored, mode 600, secret never returned), reuse a Google app for another channel (`client_from`), rename, remove, connect, per-account checklist and a Google Cloud guide. `.env` accounts stay read-only on screen.
- Tests: 59 pass (Google mocked). Browser check: added a fake account, saw its checklist, removed it; file back to empty.
- Not verified: sign-in and Studio for the second account (its Google client needs the redirect address registered), the reports charts with real data (needs the Analytics API on), and the add-permission flows (they send you to Google).
- Still missing: posting one video to several accounts at once.

## 2026-11-19 - Post to several accounts at once, guarded Connect
- `POST /api/youtube/posts/multi`: `yt_publish.py` fans one upload job out to every chosen account with `asyncio.gather`; each task picks its own account (own context copy), uses its own token, writes its own history row (shared `group_id`) and stashes its own thumbnail. One account failing does not stop the rest (`items` + `errors`). The single `POST /posts` now uses the same code.
- Screen: "Post to" checklist in the publish step (only signed-in accounts can be ticked), button shows the count, result message lists successes and failures; the form is kept if every account failed.
- `/connect?check=true` (used by the screens): asks Google first and returns 409 with the fix instead of sending the user to `redirect_uri_mismatch`. The message offers both fixes (register the redirect address, or use a Desktop client).
- Fixes: a label such as `@GenVideoAIforKids` now gets a sensible key; tests no longer read the real `youtube_accounts.json` (two failed because of it).
- Real state: `dgmgenmedia` (not phone-verified) and `@GenVideoAIforKids` (shares its Google app, verified) are signed in; `athish0204` is not (its Web client needs the redirect address registered).
- Tests: 64 pass (Google mocked). Browser: the Post to list, count, disabled unsigned account and blocked button checked; guarded Connect checked. NOT done: a real upload to two accounts (it would post to your real channels).

## 2026-11-19 - AI ticks "Made for kids" and "AI content", channel suggestions and dropdown
- `ai_signals.py`: file markers (C2PA / IPTC `trainedAlgorithmicMedia` bytes in the head and tail, AI tool names in ffprobe tags) plus the context note, plus `analyzer.classify` (vision model, judged from pictures only). `/api/analyze/youtube` now returns `youtube.suggestions` with a reason for each box. Low-confidence guesses tick nothing.
- `routes/yt_channels.py`: channel profiles (cached 5 min) and `POST /suggest`: the text model scores each signed-in channel from its own words; a kids video always goes to kids channels (taken from the channel's own kids setting or words, not from the AI's scoring), other videos stay off them; without Ollama a word-match fallback is used.
- Screen: `YtChannelPicker` dropdown, boxes ticked with reasons, Advanced opens itself, "Made for kids" / channel mismatch warning, add-channel panel from the dropdown, Connect from the dropdown (returns to the YouTube screen).
- Real run (15 s vertical sample, kids + Sora note): both boxes ticked with reasons, only the kids channel selected. Tests: 72 pass.
- Honest limits: judging "AI-generated" from pictures is unreliable, so file labels and your note carry most of the weight; no real kids video or Sora-labelled file was available, so those paths were tested with generated files and mocks.
- Found during testing: two public uploads, "Serene Seascapes for Kids", were made to dgmgenmedia and @GenVideoAIforKids at 12:06 UTC while the test browser was in use. My scripts never pressed Upload; see the notes in the chat.
