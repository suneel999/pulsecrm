from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "desk.sqlite"
IST = ZoneInfo("Asia/Kolkata")

STATUSES = (
    ("new", "New"),
    ("called", "Called"),
    ("not_picked", "Not picked"),
    ("second_call", "2nd call"),
    ("visited", "Visited"),
    ("cancelled", "Cancelled"),
)
STATUS_KEYS = {key for key, _ in STATUSES}
SERVICES = (
    "Consultation",
    "ECG",
    "2D Echo",
    "TMT",
    "Angiogram",
    "Angioplasty",
    "Lab tests",
    "Health package",
    "Other",
)


def now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def today() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


def clean(value, max_len: int = 300) -> str:
    text = re.sub(r"[\r\n]+", " ", str(value or "")).strip()
    text = re.sub(r"<[^>]+>", "", text)
    return text[:max_len]


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT DEFAULT '',
            department TEXT DEFAULT '',
            doctor TEXT DEFAULT '',
            preferred_date TEXT DEFAULT '',
            preferred_time TEXT DEFAULT '',
            source TEXT DEFAULT 'website',
            page TEXT DEFAULT '',
            status TEXT DEFAULT 'new',
            notes TEXT DEFAULT '',
            services TEXT DEFAULT '[]',
            service_other TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(appointments)").fetchall()}
    if "external_id" not in cols:
        conn.execute("ALTER TABLE appointments ADD COLUMN external_id TEXT DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_desk_status ON appointments(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_desk_created ON appointments(created_at)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_desk_external ON appointments(external_id) "
        "WHERE external_id IS NOT NULL AND external_id != ''"
    )
    conn.commit()
    return conn


def _row(row: sqlite3.Row | None) -> dict | None:
    if not row:
        return None
    data = dict(row)
    try:
        data["services_list"] = json.loads(data.get("services") or "[]")
    except json.JSONDecodeError:
        data["services_list"] = []
    return data


def create(data: dict) -> dict:
    name = clean(data.get("name"), 120)
    phone = clean(data.get("phone"), 30)
    if not name or not phone:
        raise ValueError("Name and phone are required.")
    stamp = clean(data.get("created_at"), 40) or now()
    status = clean(data.get("status"), 20) or "new"
    if status not in STATUS_KEYS:
        status = "new"
    services = data.get("services") or []
    if isinstance(services, str):
        services = [item.strip() for item in services.split(",") if item.strip()]
    conn = connect()
    conn.execute(
        """
        INSERT INTO appointments (
            name, phone, email, department, doctor, preferred_date, preferred_time,
            source, page, status, notes, services, service_other, external_id,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            phone,
            clean(data.get("email"), 160),
            clean(data.get("department"), 80),
            clean(data.get("doctor"), 160),
            clean(data.get("preferred_date") or data.get("date"), 40),
            clean(data.get("preferred_time") or data.get("time"), 40),
            clean(data.get("source") or "website", 40),
            clean(data.get("page"), 80),
            status,
            clean(data.get("notes") or data.get("message"), 2000),
            json.dumps(services),
            clean(data.get("service_other"), 200),
            clean(data.get("external_id"), 40),
            stamp,
            now(),
        ),
    )
    row_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.commit()
    row = conn.execute("SELECT * FROM appointments WHERE id = ?", (row_id,)).fetchone()
    conn.close()
    return _row(row)


def upsert_app(rows: list[dict]) -> dict:
    """Import Hi Pulse app requests. Never overwrite staff status/notes/services."""
    added = 0
    refreshed = 0
    conn = connect()
    for item in rows:
        external_id = clean(item.get("external_id"), 40)
        if not external_id:
            continue
        existing = conn.execute(
            "SELECT id, notes FROM appointments WHERE external_id = ?",
            (external_id,),
        ).fetchone()
        name = clean(item.get("name"), 120)
        phone = clean(item.get("phone"), 30)
        if not name or not phone:
            continue
        created = clean(item.get("created_at"), 40) or now()
        preferred_date = clean(item.get("preferred_date"), 40)
        preferred_time = clean(item.get("preferred_time"), 40)
        if existing:
            conn.execute(
                """
                UPDATE appointments
                SET name = ?, phone = ?, preferred_date = ?, preferred_time = ?,
                    doctor = ?, source = 'app', page = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    phone,
                    preferred_date,
                    preferred_time,
                    clean(item.get("doctor") or "Hi Pulse App", 160),
                    clean(item.get("page") or "hi-pulse-app", 80),
                    now(),
                    existing["id"],
                ),
            )
            if not (existing["notes"] or "").strip() and item.get("notes"):
                conn.execute(
                    "UPDATE appointments SET notes = ? WHERE id = ?",
                    (clean(item.get("notes"), 2000), existing["id"]),
                )
            refreshed += 1
        else:
            status = clean(item.get("status"), 20) or "new"
            if status not in STATUS_KEYS:
                status = "new"
            conn.execute(
                """
                INSERT INTO appointments (
                    name, phone, email, department, doctor, preferred_date, preferred_time,
                    source, page, status, notes, services, service_other, external_id,
                    created_at, updated_at
                ) VALUES (?, ?, '', '', ?, ?, ?, 'app', ?, ?, ?, '[]', '', ?, ?, ?)
                """,
                (
                    name,
                    phone,
                    clean(item.get("doctor") or "Hi Pulse App", 160),
                    preferred_date,
                    preferred_time,
                    clean(item.get("page") or "hi-pulse-app", 80),
                    status,
                    clean(item.get("notes"), 2000),
                    external_id,
                    created,
                    now(),
                ),
            )
            added += 1
    conn.commit()
    conn.close()
    return {"added": added, "refreshed": refreshed, "total": added + refreshed}


def purge_app_before(cutoff: str) -> int:
    """Remove Hi Pulse App rows older than the desk start date (keeps To call small)."""
    day = clean(cutoff, 10)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        return 0
    conn = connect()
    cur = conn.execute(
        """
        DELETE FROM appointments
        WHERE source = 'app'
          AND (
            (created_at != '' AND created_at < ?)
            OR (created_at = '' AND preferred_date != '' AND preferred_date < ?)
          )
        """,
        (day, day),
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return int(deleted or 0)


def get(appt_id: int) -> dict | None:
    conn = connect()
    row = conn.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,)).fetchone()
    conn.close()
    return _row(row)


PAGE_SIZE = 25
VIEWS = ("fresh", "coming", "followup", "todo", "all")


def short_doctor(name: str) -> str:
    text = (name or "").split("(")[0].strip()
    return text or "—"


def format_slot(date_value: str, time_value: str) -> str:
    day = date_value or ""
    try:
        day = datetime.strptime(date_value, "%Y-%m-%d").strftime("%d %b")
    except ValueError:
        day = date_value or "No date"
    return f"{day} {time_value or ''}".strip()


def _filters(view: str = "", status: str = "", q: str = "", month: str = "") -> tuple[list[str], list, str]:
    where = ["1=1"]
    params: list = []
    order = "id DESC"
    day = today()
    if view == "fresh":
        where.append("created_at LIKE ?")
        params.append(f"{day}%")
        order = "id DESC"
    elif view == "coming":
        where.append("preferred_date = ?")
        where.append("status NOT IN ('visited','cancelled')")
        params.append(day)
        order = "preferred_time, name, id"
    elif view == "followup":
        where.append("status IN ('called','not_picked','second_call')")
        order = "updated_at, id"
    elif view == "todo":
        where.append("status = 'new'")
        order = "id DESC"
    if status in STATUS_KEYS:
        where.append("status = ?")
        params.append(status)
    if q:
        like = f"%{q}%"
        where.append("(name LIKE ? OR phone LIKE ? OR doctor LIKE ? OR email LIKE ?)")
        params.extend([like, like, like, like])
    if month and re.match(r"^\d{4}-\d{2}$", month):
        where.append("(preferred_date LIKE ? OR created_at LIKE ?)")
        params.extend([f"{month}%", f"{month}%"])
    return where, params, order


def list_appts(status: str = "", q: str = "", day: str = "", month: str = "") -> list[dict]:
    where, params, order = _filters(status=status, q=q, month=month)
    if day:
        where.append("(preferred_date = ? OR created_at LIKE ?)")
        params.extend([day, f"{day}%"])
    conn = connect()
    rows = conn.execute(
        f"SELECT * FROM appointments WHERE {' AND '.join(where)} ORDER BY {order} LIMIT 400",
        params,
    ).fetchall()
    conn.close()
    return [_row(row) for row in rows]


def list_page(view: str = "fresh", status: str = "", q: str = "", page: int = 1) -> tuple[list[dict], int]:
    if view not in VIEWS:
        view = "fresh"
    page = max(1, int(page or 1))
    where, params, order = _filters(view=view, status=status, q=q)
    conn = connect()
    total = conn.execute(
        f"SELECT COUNT(*) FROM appointments WHERE {' AND '.join(where)}",
        params,
    ).fetchone()[0]
    offset = (page - 1) * PAGE_SIZE
    rows = conn.execute(
        f"SELECT * FROM appointments WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?",
        [*params, PAGE_SIZE, offset],
    ).fetchall()
    conn.close()
    return [_row(row) for row in rows], int(total)


def update(appt_id: int, data: dict) -> dict:
    row = get(appt_id)
    if not row:
        raise ValueError("Appointment not found.")
    status = clean(data.get("status"), 20) or row["status"]
    if status not in STATUS_KEYS:
        raise ValueError("Invalid status.")
    notes = data.get("notes")
    if notes is None:
        notes = row["notes"]
    else:
        notes = clean(notes, 2000)
    services = data.get("services")
    if services is None:
        services_json = row["services"]
    else:
        if isinstance(services, str):
            services = [item.strip() for item in services.split(",") if item.strip()]
        services = [item for item in services if item in SERVICES]
        services_json = json.dumps(services)
    other = data.get("service_other")
    if other is None:
        other = row["service_other"]
    else:
        other = clean(other, 200)
    conn = connect()
    conn.execute(
        """
        UPDATE appointments
        SET status = ?, notes = ?, services = ?, service_other = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, notes, services_json, other, now(), appt_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,)).fetchone()
    conn.close()
    return _row(updated)


def stats() -> dict:
    conn = connect()
    day = today()
    month = day[:7]
    result = {
        "new": conn.execute("SELECT COUNT(*) FROM appointments WHERE status = 'new'").fetchone()[0],
        "today": conn.execute(
            "SELECT COUNT(*) FROM appointments WHERE created_at LIKE ?", (f"{day}%",)
        ).fetchone()[0],
        "coming": conn.execute(
            "SELECT COUNT(*) FROM appointments WHERE preferred_date = ? AND status NOT IN ('visited','cancelled')",
            (day,),
        ).fetchone()[0],
        "visited_month": conn.execute(
            "SELECT COUNT(*) FROM appointments WHERE status = 'visited' AND updated_at LIKE ?",
            (f"{month}%",),
        ).fetchone()[0],
        "followup": conn.execute(
            "SELECT COUNT(*) FROM appointments WHERE status IN ('called','not_picked','second_call')"
        ).fetchone()[0],
    }
    conn.close()
    return result


def format_when(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d %b, %I:%M %p")
    except ValueError:
        return value or "—"
