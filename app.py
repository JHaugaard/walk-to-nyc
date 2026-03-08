from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import COOKIE_NAME, COOKIE_MAX_AGE, DEV_MODE
from db import init_schema, get_db
from auth import (
    get_current_user,
    validate_token,
    make_cookie_value,
    require_walker,
    require_setup_complete,
    require_admin,
)

EASTERN = ZoneInfo("America/New_York")


def today_et() -> date:
    """Return today's date in US Eastern time."""
    return datetime.now(EASTERN).date()


# ── Hardcoded waypoint candidates (dev) ─────────────────────────────
# In prod, these come from a maps API call. The UI pattern stays the same.

WAYPOINT_CANDIDATES = {
    "Sara": {
        "origin": "Sara's Start (Columbus, OH)",
        "total_miles": 540.0,
        "candidates": [
            {"name": "Zanesville, OH", "mile_marker": 65},
            {"name": "Wheeling, WV", "mile_marker": 140},
            {"name": "Pittsburgh, PA", "mile_marker": 195},
            {"name": "Johnstown, PA", "mile_marker": 255},
            {"name": "Altoona, PA", "mile_marker": 295},
            {"name": "Harrisburg, PA", "mile_marker": 440},
            {"name": "Philadelphia, PA", "mile_marker": 490},
            {"name": "Newark, NJ", "mile_marker": 530},
            {"name": "New York City, NY", "mile_marker": 540},
        ],
    },
    "Mariah": {
        "origin": "Mariah's Start (Scottville, NC)",
        "total_miles": 540.0,
        "candidates": [
            {"name": "Statesville, NC", "mile_marker": 80},
            {"name": "Greensboro, NC", "mile_marker": 160},
            {"name": "Roanoke, VA", "mile_marker": 265},
            {"name": "Staunton, VA", "mile_marker": 325},
            {"name": "Harrisburg, PA", "mile_marker": 440},
            {"name": "Philadelphia, PA", "mile_marker": 490},
            {"name": "Newark, NJ", "mile_marker": 530},
            {"name": "New York City, NY", "mile_marker": 540},
        ],
    },
}


def _get_candidates_for_user(user: dict) -> tuple[str, float, list[dict]]:
    """Return (origin, total_miles, candidates) for a user based on name."""
    if user["name"] == "Sara":
        data = WAYPOINT_CANDIDATES["Sara"]
    else:
        data = WAYPOINT_CANDIDATES["Mariah"]
    candidates = [
        {**wp, "selected": False, "display_order": i + 1}
        for i, wp in enumerate(data["candidates"])
    ]
    return data["origin"], data["total_miles"], candidates


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── Main route ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index(request: Request, token: str | None = None):
    # Token-based login: validate, set cookie, redirect
    if token:
        user = validate_token(token)
        if not user:
            return templates.TemplateResponse("login_landing.html", {
                "request": request,
                "heading": "Invalid Link",
                "message": "This token is not recognized. Contact the admin for a new link.",
            }, status_code=401)
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key=COOKIE_NAME,
            value=make_cookie_value(user["id"]),
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=not DEV_MODE,
            path="/",
        )
        return response

    # Cookie-based auth
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login_landing.html", {
            "request": request,
            "heading": "Welcome",
            "message": "Use the link you were given to sign in.",
        }, status_code=401)

    # Route based on role and setup status
    if user["role"] == "admin":
        return RedirectResponse(url="/admin", status_code=303)
    if not user["setup_complete"]:
        return RedirectResponse(url="/setup", status_code=303)

    # Walker with setup complete → dashboard
    return _render_dashboard(request, user)


def _get_gap_days(user_id: int) -> list[str]:
    """Return ISO dates from day-after-last-entry through yesterday."""
    db = get_db()
    row = db.execute(
        "SELECT MAX(date) AS last_date FROM daily_entry WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    db.close()

    if not row or not row["last_date"]:
        return []

    last_date = date.fromisoformat(row["last_date"])
    yesterday = today_et() - timedelta(days=1)

    if last_date >= yesterday:
        return []

    gaps = []
    current = last_date + timedelta(days=1)
    while current <= yesterday:
        gaps.append(current.isoformat())
        current += timedelta(days=1)
    return gaps


def _render_dashboard(request: Request, user: dict, flash_error: str | None = None):
    db = get_db()
    try:
        # Both walkers' progress
        progress_rows = db.execute("SELECT * FROM user_progress").fetchall()
        current = friend = None
        for row in progress_rows:
            row_dict = dict(row)
            if row_dict["user_id"] == user["id"]:
                current = row_dict
            else:
                friend = row_dict

        # Waypoints for both users
        all_waypoints = db.execute("SELECT * FROM waypoints_passed").fetchall()
        current_waypoints = [dict(w) for w in all_waypoints if w["user_id"] == user["id"]]
        friend_waypoints = [dict(w) for w in all_waypoints if friend and w["user_id"] == friend["user_id"]]

        # Recent entries for current user
        entries = db.execute(
            "SELECT * FROM recent_entries WHERE user_id = ? LIMIT 14",
            (user["id"],),
        ).fetchall()
        recent_entries = [dict(e) for e in entries]
    finally:
        db.close()

    gap_days = _get_gap_days(user["id"])

    # Pace status message
    deadline = date(2026, 9, 30)
    days_remaining = max(0, (deadline - today_et()).days)
    status_message = None
    status_class = None
    if current and current["route_total_miles"]:
        remaining_miles = current["route_total_miles"] - current["total_miles"]
        if remaining_miles <= 0:
            status_message = "You made it to NYC!"
            status_class = "status-ahead"
        elif days_remaining > 0:
            needed_pace = remaining_miles / days_remaining
            status_message = f"{days_remaining} days left — {needed_pace:.1f} mi/day to finish on time"
            status_class = "status-ahead" if needed_pace <= 3.0 else "status-behind"

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": f"Walk to NYC — {current['name']}" if current else "Walk to NYC",
        "current": current,
        "friend": friend,
        "current_waypoints": current_waypoints,
        "friend_waypoints": friend_waypoints,
        "recent_entries": recent_entries,
        "gap_days": gap_days,
        "flash_error": flash_error,
        "status_message": status_message,
        "status_class": status_class,
        "days_remaining": days_remaining,
    })


# ── Setup routes ────────────────────────────────────────────────────

@app.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, user: dict = Depends(require_walker)):
    if user["setup_complete"]:
        return RedirectResponse(url="/", status_code=303)
    origin, total_miles, _ = _get_candidates_for_user(user)
    return templates.TemplateResponse("setup.html", {
        "request": request,
        "title": "Route Setup",
        "user": user,
        "default_origin": origin,
        "default_total_miles": total_miles,
    })


@app.post("/setup")
def setup_submit(
    request: Request,
    user: dict = Depends(require_walker),
    seed_miles: float = Form(...),
):
    if user["setup_complete"]:
        return RedirectResponse(url="/", status_code=303)

    origin, total_miles, candidates = _get_candidates_for_user(user)
    destination = "Madison Square Garden, New York, NY"

    db = get_db()
    try:
        db.execute("BEGIN")
        db.execute(
            """UPDATE user SET
                route_origin_address = ?, route_dest_address = ?,
                route_total_miles = ?, seed_miles = ?, setup_complete = 1
            WHERE id = ? AND setup_complete = 0""",
            (origin, destination, total_miles, seed_miles, user["id"]),
        )
        # Still insert all waypoints for report page usage
        for i, wp in enumerate(candidates):
            db.execute(
                """INSERT INTO waypoint (user_id, name, mile_marker, display_order, selected)
                VALUES (?, ?, ?, ?, 1)""",
                (user["id"], wp["name"], wp["mile_marker"], wp["display_order"]),
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return RedirectResponse(url="/", status_code=303)


# ── Entry logging routes ────────────────────────────────────────────

@app.post("/log")
def log_miles(
    request: Request,
    user: dict = Depends(require_setup_complete),
    date_str: str = Form(..., alias="date"),
    miles: float = Form(...),
):
    # Validate date
    try:
        entry_date = date.fromisoformat(date_str)
    except ValueError:
        return _render_dashboard(request, user, flash_error="Invalid date.")

    if entry_date > today_et():
        return _render_dashboard(request, user, flash_error="Cannot log future dates.")

    if miles < 0:
        return _render_dashboard(request, user, flash_error="Miles cannot be negative.")

    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM daily_entry WHERE user_id = ? AND date = ?",
            (user["id"], date_str),
        ).fetchone()
        if existing:
            return _render_dashboard(request, user, flash_error=f"Entry already exists for {date_str}.")

        db.execute(
            "INSERT INTO daily_entry (user_id, date, miles) VALUES (?, ?, ?)",
            (user["id"], date_str, miles),
        )
        db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/", status_code=303)


@app.post("/log-zeros")
def log_zeros(request: Request, user: dict = Depends(require_setup_complete)):
    """Fill all gap days with 0 miles."""
    gap_days = _get_gap_days(user["id"])
    if not gap_days:
        return RedirectResponse(url="/", status_code=303)

    db = get_db()
    try:
        db.execute("BEGIN")
        for day in gap_days:
            db.execute(
                "INSERT OR IGNORE INTO daily_entry (user_id, date, miles) VALUES (?, ?, 0)",
                (user["id"], day),
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return RedirectResponse(url="/", status_code=303)


@app.post("/edit/{entry_id}")
def edit_entry(
    entry_id: int,
    request: Request,
    user: dict = Depends(require_setup_complete),
    new_miles: float = Form(...),
):
    if new_miles < 0:
        return _render_dashboard(request, user, flash_error="Miles cannot be negative.")

    db = get_db()
    try:
        entry = db.execute(
            "SELECT * FROM daily_entry WHERE id = ? AND user_id = ?",
            (entry_id, user["id"]),
        ).fetchone()

        if not entry:
            return _render_dashboard(request, user, flash_error="Entry not found.")

        entry_date = date.fromisoformat(entry["date"])
        if entry_date < today_et() - timedelta(days=7):
            return _render_dashboard(request, user, flash_error="Entry is older than 7 days and cannot be edited.")

        now_et = datetime.now(EASTERN).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "UPDATE daily_entry SET miles = ?, updated_at = ? WHERE id = ?",
            (new_miles, now_et, entry_id),
        )
        db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/", status_code=303)


# ── Admin routes ────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
def admin_page(
    request: Request,
    user: dict = Depends(require_admin),
    new_token: str | None = None,
    token_for: str | None = None,
):
    db = get_db()
    try:
        walkers = [dict(r) for r in db.execute("SELECT * FROM user_progress").fetchall()]
    finally:
        db.close()

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "title": "Admin Panel",
        "walkers": walkers,
        "new_token": new_token,
        "token_for": token_for,
    })


@app.post("/admin/regenerate/{target_user_id}")
def regenerate_token(
    target_user_id: int,
    request: Request,
    user: dict = Depends(require_admin),
):
    import secrets
    from auth import hash_token

    raw_token = secrets.token_urlsafe(32)
    new_hash = hash_token(raw_token)

    db = get_db()
    try:
        target = db.execute("SELECT name FROM user WHERE id = ?", (target_user_id,)).fetchone()
        if not target:
            return RedirectResponse(url="/admin", status_code=303)
        db.execute("UPDATE user SET token_hash = ? WHERE id = ?", (new_hash, target_user_id))
        db.commit()
        target_name = target["name"]
    finally:
        db.close()

    # Re-render admin page with the new token displayed
    return admin_page(request=request, user=user, new_token=raw_token, token_for=target_name)


@app.get("/admin/report/{target_user_id}", response_class=HTMLResponse)
def admin_report(
    target_user_id: int,
    request: Request,
    user: dict = Depends(require_admin),
):
    db = get_db()
    try:
        # User progress
        progress = db.execute(
            "SELECT * FROM user_progress WHERE user_id = ?", (target_user_id,)
        ).fetchone()
        if not progress:
            return RedirectResponse(url="/admin", status_code=303)
        progress = dict(progress)

        # All entries for streak calculation
        entries = db.execute(
            "SELECT date, miles FROM daily_entry WHERE user_id = ? ORDER BY date",
            (target_user_id,),
        ).fetchall()

        # Waypoints passed
        waypoints = db.execute(
            "SELECT name, mile_marker FROM waypoints_passed WHERE user_id = ? AND passed = 1",
            (target_user_id,),
        ).fetchall()

        # User info
        user_row = db.execute(
            "SELECT route_origin_address FROM user WHERE id = ?", (target_user_id,)
        ).fetchone()
    finally:
        db.close()

    # Compute longest streak (consecutive days with miles > 0)
    longest_streak = 0
    current_streak = 0
    for entry in entries:
        if entry["miles"] > 0:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0

    report = {
        "total_miles": progress["total_miles"],
        "percent_complete": progress["percent_complete"],
        "days_active": progress["days_active"],
        "total_entry_days": len(entries),
        "longest_streak": longest_streak,
        "first_entry_date": entries[0]["date"] if entries else None,
        "last_entry_date": entries[-1]["date"] if entries else None,
        "waypoints_passed": [dict(w) for w in waypoints],
    }

    return templates.TemplateResponse("report.html", {
        "request": request,
        "title": f"Report — {progress['name']}",
        "walker_name": progress["name"],
        "origin": user_row["route_origin_address"] if user_row else "Unknown",
        "report": report,
    })
