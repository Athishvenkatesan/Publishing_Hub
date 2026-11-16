# Conventions
- Backend: FastAPI, one router per resource in `routes/`, vendor calls only in `zernio.py`, status mapping in `status.py`.
- Frontend: React + Astryx (DEWA theme), one page, components in `src/components/`.
- Times: stored in UTC, shown in Asia/Dubai.
- Secrets only in `backend/.env`.
