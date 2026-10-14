from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
_token = ""
_token_at = 0.0


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _base() -> str:
    return (_env("APP_API_URL") or "https://api.thepulseheart.com").rstrip("/")


def _post(path: str, payload: dict, token: str = "") -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["token"] = token
    req = urllib.request.Request(
        f"{_base()}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"App API {path} failed ({exc.code}): {body[:200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"App API unreachable: {exc.reason}") from exc


def login(force: bool = False) -> str:
    global _token, _token_at
    import time

    if _token and not force and (time.time() - _token_at) < 6 * 3600:
        return _token
    email = _env("APP_API_EMAIL")
    password = _env("APP_API_PASSWORD")
    if not email or not password:
        raise RuntimeError("APP_API_EMAIL / APP_API_PASSWORD not set.")
    data = _post("/admin/login", {"email": email, "password": password})
    token = (data.get("token") or "").strip()
    if not token:
        raise RuntimeError(data.get("message") or "App login failed.")
    _token = token
    _token_at = time.time()
    return _token


def utc_to_ist(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return text[:19].replace("T", " ")


def map_status(app_status: str) -> str:
    key = (app_status or "").strip().lower()
    if key in {"pending", "new", ""}:
        return "new"
    if key in {"accepted", "confirmed", "called"}:
        return "called"
    if key in {"visited", "completed", "done"}:
        return "visited"
    if key in {"cancelled", "canceled", "rejected"}:
        return "cancelled"
    return "new"


def normalize(row: dict) -> dict:
    first = (row.get("first_name") or "").strip()
    last = (row.get("last_name") or "").strip()
    name = f"{first} {last}".strip() or "App patient"
    created = utc_to_ist(str(row.get("accepted_at") or ""))
    preferred_date = created[:10] if created else ""
    preferred_time = ""
    if len(created) >= 16:
        try:
            preferred_time = datetime.strptime(created, "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p").lstrip("0")
        except ValueError:
            preferred_time = created[11:16]
    notes_bits = []
    if row.get("description"):
        notes_bits.append(str(row["description"]).strip())
    if row.get("remarks"):
        notes_bits.append(str(row["remarks"]).strip())
    return {
        "external_id": str(row.get("appointment_id") or ""),
        "name": name,
        "phone": str(row.get("mobile_number") or "").strip(),
        "email": "",
        "department": "",
        "doctor": "Hi Pulse App",
        "preferred_date": preferred_date,
        "preferred_time": preferred_time,
        "source": "app",
        "page": "hi-pulse-app",
        "status": map_status(str(row.get("status") or "")),
        "notes": " · ".join(notes_bits),
        "created_at": created,
        "app_status": str(row.get("status") or ""),
    }


def fetch_appointments(limit: int = 50, max_pages: int = 20) -> list[dict]:
    token = login()
    rows: list[dict] = []
    page = 1
    while page <= max_pages:
        try:
            data = _post(
                "/requests/getAppointments",
                {"page": page, "limit": limit},
                token=token,
            )
        except RuntimeError:
            token = login(force=True)
            data = _post(
                "/requests/getAppointments",
                {"page": page, "limit": limit},
                token=token,
            )
        batch = data.get("data") or []
        if not batch:
            break
        rows.extend(normalize(item) for item in batch)
        total_pages = int(data.get("totalPages") or page)
        if page >= total_pages:
            break
        page += 1
    return [row for row in rows if row.get("external_id") and row.get("phone")]
