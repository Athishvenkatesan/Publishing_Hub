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
- New screen `#/facebook` (nav bar links both screens): checks the Meta token (user, permissions, Pages, what it can do for Facebook / Instagram / WhatsApp), publishes a video to a Facebook Page now or scheduled (10 minutes to 75 days ahead), own history.
- Backend: `meta.py` (only Meta-aware module), `routes/facebook.py`, token in `backend/.env` as `META_ACCESS_TOKEN` (never commit). Page tokens stay on the server.
- Graph API Explorer tokens last about 1 hour. When one expires the screen says so. For longer use, exchange it for a long-lived token (needs the app secret).
- Facebook rows are kept out of the Instagram + YouTube history. Instagram and WhatsApp via Meta are checked but not wired yet.
- Tests: 12 pass (4 new, Meta mocked). No real Facebook post has been made.
