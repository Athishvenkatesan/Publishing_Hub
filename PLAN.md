# DGM Publishing Hub - POC plan

Status: POC BUILT. See PROJECT.md for how to run it.

## 1. Goal
One screen. A user picks a video, chooses social accounts, sets a date and time, and clicks Publish.
The video posts to the chosen accounts automatically at that time. A status table below the form
shows what happened to every post.

Out of scope for the POC: DGM approval flow, classification guard, Arabic/English pairs, metrics,
withdraw/delete, multi-user roles. (They are listed in DGM-Publishing-Hub-Analysis.pdf, section 2.)

## 2. The screen
```
+--------------------------------------------------------------+
| DGM Publishing Hub - POC                                     |
| 1. Video      [ Choose file ]  clip.mp4  (preview)           |
| 2. Caption    [ text ]                                       |
| 3. Accounts   [x] YouTube  [x] Instagram  [ ] TikTok ...     |
| 4. When       ( ) Now   (o) Schedule  [date] [time] [tz]     |
|                                        [ Publish ]           |
+--------------------------------------------------------------+
| Status report                                                |
| Video | Account | Scheduled for | Status | Post link | Error  |
+--------------------------------------------------------------+
```
Status values: QUEUED, UPLOADING, SCHEDULED, PUBLISHING, PUBLISHED, FAILED. The table refreshes every 10 s.

## 3. How it works
1. Browser uploads the file to our API (multipart).
2. API validates type (mp4/mov) and size, stores the file, creates one `post` row and one `post_target` row per account.
3. API hands the video, caption, accounts and time to the Publishing Adapter.
4. Adapter calls the provider with the schedule time (provider-native scheduling), or publishes now.
5. Provider webhook (or a 10 s poll as fallback) updates each target's status and post URL.
6. The table reads from our database.

Why provider-native scheduling: the post still goes out if our server is down at the scheduled time.
If the chosen provider lacks scheduling, fall back to a local scheduler (APScheduler) that calls publish at the due time.

## 4. Stack (DAK defaults)
| Layer | Choice |
|---|---|
| Frontend | React 19 + Vite, Astryx + DEWA theme, one page |
| Backend | FastAPI, SQLAlchemy 2 async, Pydantic |
| Database | SQLite (POC is local-only; Postgres later) |
| Provider | Behind an adapter. POC default: Zernio (2 accounts free, full API). Alternatives: Post for Me, Outstand, Postiz |
| Storage | Local folder `backend/uploads/` |
| Ports | Frontend 3100, Backend 8100 (both free on this machine today) |

Note: provider fetches the video by URL, so a local file needs a public link while testing
(a tunnel such as Cloudflare Tunnel or ngrok), or we upload the file to the provider's media endpoint if it has one.

## 5. Folder layout (to be created in step 1 of the build)
```
POC/
  PLAN.md  PROJECT.md  CONVENTIONS.md
  backend/  app.py  routes/posts.py  adapters/base.py  adapters/zernio.py  models.py  tests/
  frontend/ src/pages/Publish.jsx  src/components/StatusTable.jsx
```

## 6. Build steps and status
| # | Step | Output | Status |
|---|---|---|---|
| 0 | Create POC folder and plan | POC/PLAN.md | DONE |
| 1 | Receive inputs (section 7) | provider choice, test accounts, API key | DONE (key and Instagram + YouTube accounts received) |
| 2 | Scaffold project (`dak init`), ports, PROJECT.md | running empty app | DONE |
| 3 | Connect 1-2 test social accounts at the provider | accounts listed by API | DONE |
| 4 | Adapter: list accounts, publish now with a test video | one real post | READY - waiting for your first click |
| 5 | Upload endpoint and database (post, post_target) | file saved, rows created | DONE |
| 6 | Schedule: date, time, timezone to provider | post fires at set time | DONE (tested with mocks) |
| 7 | Status updates: webhook or poll | table status changes by itself | DONE (poll) |
| 8 | Single screen UI and status table | form + table working | DONE |
| 9 | Tests (publish now, scheduled, failure) and browser check | all pass | DONE (4 backend tests, browser check) |
| 10 | Demo run and short result note | 5-minute demo | NEXT |

Estimate: 3 to 5 working days after the inputs arrive. Most of the risk is in step 3 (network account
approval), not in the code.

## 7. What I need from you
1. Provider: Zernio for the POC, or another from the shortlist?
2. Networks: which to test (YouTube, Instagram, TikTok, Facebook, X, LinkedIn)?
3. Test accounts: use throwaway accounts, not the entity's real ones. Who owns them and can log in to approve?
4. Provider account and API key (put it in `.env`, never in chat or in the repo).
5. Real posting or dry run? A dry run shows the full flow without publishing.
6. Timezone for the date and time picker (Dubai, UTC+4?).
7. Video rules: maximum file size and length, and orientation (9:16 only, or also 16:9).
8. Caption: one text for all accounts, or one per account? Title and hashtags needed (YouTube needs a title)?
9. Sign-in: none for the POC, or the DAK admin password?
10. Status table: any other columns, such as a link to the post or the retry button?
11. Sample video: one short clip (under 30 s) for testing.
12. Does the machine have a way to expose a public URL (tunnel) for the provider to fetch the video? If not, I will pick the provider media-upload route.

## 8. Risks
| Risk | Effect | Handling |
|---|---|---|
| TikTok and Instagram need audited or business-linked apps | Posts forced private or blocked | Start with YouTube and Facebook; use provider managed keys for the POC |
| YouTube daily upload quota | About 6 uploads a day per project on own app | Fine for a POC |
| Scheduled time in wrong timezone | Post at wrong hour | Store UTC, show the zone next to the picker |
| Local file not reachable by provider | Publish fails | Tunnel or provider upload endpoint |
