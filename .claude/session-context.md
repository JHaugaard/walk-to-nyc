# Session Context

## Current Focus
walk-to-nyc: Deployed to Fly.io with CI/CD, custom domain live

## MCP Servers Added This Session
| Server | Status |
|--------|--------|
| (none) | — |

## Key Decisions
1. FastAPI over Flask — Pydantic maps to handoff JSON, dependency injection fits auth model, free Swagger docs
2. Flat project structure — no routers/, no ORM, no migration framework. 8 routes in app.py.
3. Sync sqlite3 (not aiosqlite) — microsecond ops for 3 users, simpler code
4. itsdangerous for cookie signing — URLSafeSerializer signs user_id, httponly/samesite/secure
5. Waypoint setup UI: "pick 6 from list" pattern — hardcoded candidates for dev, maps API feeds prod
6. Gap-fill enforced: oldest gap day first, or "fill all with 0" shortcut
7. Status message: pace-based (mi/day needed), threshold at 3.0 mi/day for ahead/behind
8. Deploy to Fly.io instead of fighting localhost issues — CI/CD via GitHub Actions
9. config.py guards `.env.local` with existence check (file absent in Docker)

## Artifacts Produced
- `app.py` — FastAPI app with 8 routes (dashboard, setup, log, edit, log-zeros, admin, regen, report)
- `db.py` — SQLite schema DDL (3 tables, 3 views, 2 indexes), connection helper
- `auth.py` — Token hashing, cookie signing, 4 FastAPI dependencies
- `config.py` — Settings from env vars (conditional .env.local load)
- `init_db.py` — One-time seed script (3 users, prints tokens)
- `templates/` — base, dashboard, setup, admin, report, login_landing (6 templates)
- `static/style.css` — Full CSS with dark mode, split-screen, responsive
- `Dockerfile` + `fly.toml` — Deployment config (volume at /data, DB_PATH=/data/walk.db)
- `.dockerignore` — Clean image excludes
- `.github/workflows/deploy.yml` — GitHub Actions CI/CD (push to main → fly deploy)

## Deployment
- **App URL**: walk-to-nyc.fly.dev
- **Custom domain**: walk.haugaard.app
- **Region**: iad
- **Volume**: walk_data mounted at /data (1GB, SQLite DB)
- **Secret**: COOKIE_SECRET set via `fly secrets`
- **CI/CD**: GitHub Actions, secret `FLY_API_TOKEN`
- **DNS**: Cloudflare A + AAAA records (gray cloud), `fly certs add` for SSL
- **DB reset**: `fly ssh console -C "rm /data/walk.db && python init_db.py"`

## What's Next
- Visual polish pass (user poking around live site)
- Maps API integration for real waypoint candidates (future session)

## Notes
- Fly shared IPv4 requires both A and AAAA records for custom domains
- `fly certs add <domain>` required before custom domain works (triggers SSL provisioning)
- DB seeded with 3 users (Sara, Mariah, Admin) — tokens captured by user

## Session Status
Completed: 2026-02-15
Servers cleaned: none needed
