"""Pulse Heart WhatsApp appointment Flow screen logic (Meta Appointment booking template)."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import db

IST = ZoneInfo("Asia/Kolkata")

# Matches Meta Flow Builder Appointment booking template field ids.
DEPARTMENTS = [
    {"id": "cardiology", "title": "Cardiology"},
    {"id": "neurology", "title": "Neurology"},
    {"id": "pulmonology", "title": "Pulmonology"},
    {"id": "gastroenterology", "title": "Gastroenterology"},
    {"id": "orthopedics", "title": "Orthopedics"},
    {"id": "general_medicine", "title": "General Medicine"},
    {"id": "radiology", "title": "Radiology"},
]

LOCATIONS = [
    {"id": "miyapur", "title": "Pulse Heart · Miyapur, Hyderabad"},
]

DEPT_TITLE = {item["id"]: item["title"] for item in DEPARTMENTS}
LOC_TITLE = {item["id"]: item["title"] for item in LOCATIONS}

# Desk department names used by website/CRM filters
DEPT_CRM = {
    "cardiology": "Cardiology",
    "neurology": "Neurology",
    "pulmonology": "Pulmonology",
    "gastroenterology": "Gastroenterology",
    "orthopedics": "Orthopedics",
    "general_medicine": "Internal Medicine",
    "radiology": "Radiology & Imaging",
}


def _upcoming_dates(days: int = 14) -> list[dict]:
    today = datetime.now(IST).date()
    out = []
    for offset in range(0, days + 7):
        day = today + timedelta(days=offset)
        if day.weekday() == 6:  # Sunday closed for OP
            continue
        out.append(
            {
                "id": day.isoformat(),
                "title": day.strftime("%a %d %b %Y"),
            }
        )
        if len(out) >= days:
            break
    return out


def _times_for_department(department_id: str) -> list[dict]:
    # General Medicine has afternoon + evening slots at Pulse
    if department_id == "general_medicine":
        slots = [
            "10:30 AM",
            "11:00 AM",
            "11:30 AM",
            "12:00 PM",
            "12:30 PM",
            "01:00 PM",
            "01:30 PM",
            "06:30 PM",
            "07:00 PM",
            "07:30 PM",
        ]
    else:
        slots = [
            "10:30 AM",
            "11:00 AM",
            "11:30 AM",
            "12:00 PM",
            "12:30 PM",
            "01:00 PM",
            "01:30 PM",
            "02:00 PM",
            "02:30 PM",
            "03:00 PM",
            "03:30 PM",
        ]
    return [{"id": slot, "title": slot} for slot in slots]


def _appointment_screen(
    department: str = "",
    location: str = "",
    date: str = "",
    time: str = "",
) -> dict:
    dates = _upcoming_dates()
    times = _times_for_department(department) if department else _times_for_department("cardiology")
    return {
        "screen": "APPOINTMENT",
        "data": {
            "department": DEPARTMENTS,
            "location": LOCATIONS,
            "date": dates,
            "time": times,
            "is_location_enabled": bool(department),
            "is_date_enabled": bool(department) and bool(location),
            "is_time_enabled": bool(department) and bool(location) and bool(date),
        },
    }


def _find_title(options: list[dict], option_id: str) -> str:
    for item in options:
        if item["id"] == option_id:
            return item["title"]
    return option_id or "—"


def get_next_screen(decrypted_body: dict) -> dict:
    action = decrypted_body.get("action")
    screen = decrypted_body.get("screen")
    data = decrypted_body.get("data") or {}
    flow_token = decrypted_body.get("flow_token") or ""
    version = decrypted_body.get("version") or "3.0"

    # Health check from Meta
    if action == "ping":
        return {"version": version, "data": {"status": "active"}}

    # Client-side error notification
    if data.get("error"):
        return {"version": version, "data": {"acknowledged": True}}

    if action == "INIT":
        payload = _appointment_screen()
        payload["data"]["is_location_enabled"] = False
        payload["data"]["is_date_enabled"] = False
        payload["data"]["is_time_enabled"] = False
        payload["version"] = version
        return payload

    if action != "data_exchange":
        raise ValueError(f"Unhandled action: {action}")

    if screen == "APPOINTMENT":
        # Cascading dropdown refresh (Meta Appointment template).
        # Continue usually navigates to DETAILS in Flow JSON; keep returning APPOINTMENT here.
        department = str(data.get("department") or "")
        location = str(data.get("location") or "")
        date = str(data.get("date") or "")
        time = str(data.get("time") or "")
        response = _appointment_screen(department, location, date, time)
        response["version"] = version
        return response

    if screen == "DETAILS":
        department = str(data.get("department") or "")
        location = str(data.get("location") or "")
        date = str(data.get("date") or "")
        time = str(data.get("time") or "")
        name = str(data.get("name") or "").strip()
        email = str(data.get("email") or "").strip()
        phone = str(data.get("phone") or "").strip()
        more = str(data.get("more_details") or "").strip()

        dept_title = DEPT_TITLE.get(department, department)
        loc_title = LOC_TITLE.get(location, location)
        date_title = _find_title(_upcoming_dates(21), date) if date else date

        appointment = f"{dept_title} at {loc_title}\n{date_title} at {time}"
        details = f"Name: {name}\nEmail: {email}\nPhone: {phone}"
        if more:
            details += f'\n"{more}"'

        return {
            "version": version,
            "screen": "SUMMARY",
            "data": {
                "appointment": appointment,
                "details": details,
                "department": department,
                "location": location,
                "date": date,
                "time": time,
                "name": name,
                "email": email,
                "phone": phone,
                "more_details": more,
            },
        }

    if screen == "SUMMARY":
        name = str(data.get("name") or "").strip()
        phone = str(data.get("phone") or "").strip()
        email = str(data.get("email") or "").strip()
        department = str(data.get("department") or "")
        date = str(data.get("date") or "")
        time = str(data.get("time") or "")
        more = str(data.get("more_details") or "").strip()

        if not name or not phone:
            return {
                "version": version,
                "screen": "DETAILS",
                "data": {
                    "error_message": "Name and phone are required.",
                    **{k: data.get(k, "") for k in (
                        "department", "location", "date", "time", "name", "email", "phone", "more_details"
                    )},
                },
            }

        try:
            db.create(
                {
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "department": DEPT_CRM.get(department, DEPT_TITLE.get(department, department)),
                    "doctor": "",
                    "preferred_date": date,
                    "preferred_time": time,
                    "notes": more or "Booked via WhatsApp Flow",
                    "source": "whatsapp",
                    "page": "whatsapp-flow",
                    "status": "new",
                }
            )
        except ValueError as exc:
            return {
                "version": version,
                "screen": "DETAILS",
                "data": {
                    "error_message": str(exc),
                    "department": department,
                    "location": data.get("location") or "",
                    "date": date,
                    "time": time,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "more_details": more,
                },
            }

        return {
            "version": version,
            "screen": "SUCCESS",
            "data": {
                "extension_message_response": {
                    "params": {
                        "flow_token": flow_token,
                        "department": DEPT_CRM.get(department, department),
                        "date": date,
                        "time": time,
                    }
                }
            },
        }

    if screen == "TERMS":
        return {"version": version, "screen": "TERMS", "data": {}}

    raise ValueError(f"Unhandled screen: {screen}")
