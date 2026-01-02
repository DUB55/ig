# Instagram Reel Extractor (Flask backend + Static PWA frontend)

**What this repo is**
- A minimal Flask backend that attempts to extract a direct MP4 URL from Instagram posts/reels using server-side requests with an Instagram session cookie.
- A simple static PWA frontend (index.html + main.js + service worker) that calls the backend.

**DISCLAIMER & IMPORTANT**
- Scraping or bypassing platform protections may violate Instagram / Meta Terms of Service. Use responsibly and only on content you have rights to process.
- Instagram actively changes endpoints, rate-limits, and treats scraping aggressively. This tool **may break** and requires maintaining a valid session & IP strategy.
- Do **NOT** put real Instagram session cookies into public repositories.

---

## Files
- `server.py` — Flask backend. Serves frontend and provides `POST /api/extract-reel`.
- `frontend/index.html` — Static PWA frontend.
- `frontend/static/main.js` — Frontend JS logic calling backend.
- `frontend/static/sw.js` — Simple service worker caching.
- `config.example.json` — example config file (if you prefer file-based config).

## Environment variables (recommended)
Create environment variables before running the server (or create `config.json` using the example):
- `INSTAGRAM_SESSIONID` — your `sessionid` cookie value from Instagram.
- `INSTAGRAM_DS_USER_ID` — your `ds_user_id` cookie value from Instagram.
- `FLASK_ENV` (optional) — e.g. `development`.

**Do not** commit a file containing real credentials.

## Quick local run
1. Create a python venv and install:
```bash
python -m venv venv
source venv/bin/activate    # on Windows: venv\Scripts\activate
pip install -r requirements.txt
