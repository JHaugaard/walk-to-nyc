# Project Learnings

Persistent knowledge captured from sessions. This file accumulates useful discoveries, quirks, and decisions that should be remembered across sessions.

<!-- Entries added by /session-end -->

## 2026-02-15 — Briefing & Data Platform Session
- **User is zero-coder; learning focus is architectural judgment, not implementation.** AI partners write all code. Value is in strengthening insights and discretion — knowing *when* to reach for which tool, not *how* to use it.
- **Python/FastAPI as preferred stack for AI-assisted development.** Claude Code writes excellent Python; debugging conversations are smoothest in Python. For a zero-coder with AI partners, "which language does my AI write best" is the real framework question.

## 2026-02-15 — FastAPI Backend Build Session
- **`uv` is the available package manager on vps4.** No pip or python3-venv installed; can't sudo. Use `uv venv .venv` and `uv pip install -r requirements.txt`. Works great and is faster than pip anyway.
- **Local dev requires SSH tunnel.** Code lives on vps4 (72.61.11.102, user: john, `ssh vps4`). To view in local browser: `ssh -L 8000:localhost:8000 vps4`, then `uvicorn app:app --reload --port 8000` on VPS, then `localhost:8000` in browser.

## 2026-02-15 — UI Polish & Maps Session
- **Jinja2 `format()` crashes on None.** `"%.0f"|format(None)` throws a 500. Always guard format calls with `{% if value %}` for nullable DB columns (e.g., `route_total_miles` before setup is complete). This caused a production 500 in the friend panel.
- **Leaflet + OpenStreetMap for route maps (no API key).** Replaced waypoint milestone track with Leaflet CDN (~40KB) + OpenStreetMap tiles. Hardcoded ~18 lat/lng points per route, linear interpolation for progress position. Free, no billing, no API key. `scrollWheelZoom: false` prevents page-scroll hijack; pinch/buttons still work.
