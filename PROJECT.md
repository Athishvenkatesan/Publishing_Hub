---
goal: Prove one screen can upload a video and publish it now or at a set time to connected social accounts
domain: DGM publishing hub
audience: DGM team
status: building
---
# DGM Publishing Hub POC

## Current State (13 Nov 2026)
- Screen works: upload clip, caption, pick accounts, publish now or schedule (Asia/Dubai), history table with status and post link.
- Provider: Zernio. Connected accounts: Instagram `aivideo.3321`, YouTube `athishvenkatesan9293`.
- Backend tests pass (4). Frontend builds. A real post has NOT been published yet (waiting for the user's first click).

## Run
Backend: `cd backend && .venv/bin/uvicorn app:app --port 8100`
Frontend: `cd frontend && npm run dev` then open http://localhost:3100
Tests: `cd backend && .venv/bin/pytest -q`
Key lives in `backend/.env` (ZERNIO_API_KEY). Never commit it.

## Deviation note
Not scaffolded with `dak init`: this is a single-screen POC. SQLite instead of Postgres, no Docker, no auth, no /journey pages. Revisit if the POC becomes the real hub.

## Known limits
- Statuses refresh when the history is read (every 10 s), not by webhook.
- No withdraw or retry button yet.
- Instagram needs a professional account; YouTube uploads are quota-limited.

## 2026-11-13 - in-app account management and new layout
- Accounts are managed inside the app (slide-in panel): `GET /api/accounts`, `POST /api/accounts/connect` (Zernio OAuth link, returns to the app), `DELETE /api/accounts/{id}`. No need to open zernio.com.
- New layout: green hero band with live counts, three fluid columns (upload, text, time + live post previews), history below.
- Zernio free plan allows 2 connected accounts; connecting a third returns a 402 message that the panel shows.
