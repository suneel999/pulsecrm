"""Pulse Heart WhatsApp appointment Flow screen logic (Meta Appointment booking template)."""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

import db

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_LOCATION = "miyapur"
DEFAULT_LOCATION_TITLE = "Pulse Heart · Miyapur"

# Dropdown titles must be ≤30 chars (WhatsApp Flows limit).
DEPARTMENTS = [
    {"id": "cardiology", "title": "Cardiology"},
    {"id": "neurology", "title": "Neurology"},
    {"id": "pulmonology", "title": "Pulmonology"},
    {"id": "gastroenterology", "title": "Gastroenterology"},
    {"id": "orthopedics", "title": "Orthopedics"},
    {"id": "general_medicine", "title": "General Medicine"},
    {"id": "radiology", "title": "Radiology"},
]

DEPT_TITLE = {item["id"]: item["title"] for item in DEPARTMENTS}

DEPT_CRM = {
    "cardiology": "Cardiology",
    "neurology": "Neurology",
    "pulmonology": "Pulmonology",
    "gastroenterology": "Gastroenterology",
    "orthopedics": "Orthopedics",
    "general_medicine": "Internal Medicine",
    "radiology": "Radiology & Imaging",
}

# Per-department doctors only (never shared across depts).
DOCTORS_BY_DEPT: dict[str, list[dict]] = {
    "cardiology": [
        {
            "id": "mukharjee",
            "title": "Dr. M.S.S. Mukharjee",
            "crm": "Dr. M.S.S. Mukharjee (Sr. Interventional Cardiologist, MD, DM, DNB)",
        },
        {
            "id": "movva_srinivas",
            "title": "Dr. Movva Srinivas",
            "crm": "Dr. Movva Srinivas (MD DM Cardiology - NIMS, FICPS Paris, France)",
        },
        {
            "id": "vinod_unni",
            "title": "Dr. Vinod K. Unni",
            "crm": "Dr. Vinod K. Unni (MD, DM Cardiology)",
        },
        {
            "id": "kranti_chintala",
            "title": "Dr. Kranti K. Chintala",
            "crm": "Dr. Kranti Kumar Chintala (MBBS, MBA, ISB - Health Care Management)",
        },
        {
            "id": "kiran_kumar",
            "title": "Dr. Kanjrla Kiran Kumar",
            "crm": "Dr. Kanjrla Kiran Kumar (MD DM Cardiology)",
        },
        {
            "id": "vikash_shukla",
            "title": "Dr. Vikash Shukla",
            "crm": "Dr. Vikash Shukla (MBBS, PGDCC Cardiology, MRPC-UK)",
        },
    ],
    "neurology": [
        {
            "id": "anand_karnam",
            "title": "Dr. Anand Karnam",
            "crm": "Dr. Anand Karnam (Consultant Neurophysician & Headache Specialist)",
        },
    ],
    "pulmonology": [
        {
            "id": "vikasna_reddy",
            "title": "Dr. K. Vikasna Reddy",
            "crm": "Dr. K. Vikasna Reddy (MBBS, MD Pulmonary Medicine, IDCCM)",
        },
    ],
    "gastroenterology": [
        {
            "id": "anita_reddy",
            "title": "Dr. P. Anita Reddy",
            "crm": "Dr. P. Anita Reddy (MBBS, MD Internal Medicine, DM Gastroenterology)",
        },
    ],
    "orthopedics": [
        {
            "id": "sai_chandra",
            "title": "Dr. Sai Chandra Malladi",
            "crm": "Dr. Sai Chandra Malladi (MBBS, MS Ortho, FIASS, FIJR)",
        },
    ],
    "general_medicine": [
        {
            "id": "nithin_katragadda",
            "title": "Dr. Nithin Katragadda",
            "crm": "Dr. Nithin Katragadda (MBBS, MD General Medicine, Diploma in Diabetology)",
        },
        {
            "id": "tanoj_batchu",
            "title": "Dr. Tanoj Batchu",
            "crm": "Dr. Tanoj Batchu (MBBS, MD Internal Medicine)",
        },
    ],
    "radiology": [
        {
            "id": "naga_balaji",
            "title": "Dr. K. Naga Balaji",
            "crm": "Dr. Kuncham Naga Balaji (MD DM Radiology)",
        },
    ],
}

DEFAULT_SLOTS = [
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

MOVVA_SLOTS = [
    "09:00 AM",
    "09:30 AM",
    "10:00 AM",
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
]

GENERAL_MED_SLOTS = [
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


def _parse_slot(label: str) -> dtime:
    return datetime.strptime(label, "%I:%M %p").time()


def _slot_options(labels: list[str]) -> list[dict]:
    return [{"id": s, "title": s} for s in labels]


def _doctors_for(department_id: str) -> list[dict]:
    return [
        {"id": d["id"], "title": d["title"]}
        for d in DOCTORS_BY_DEPT.get(department_id, [])
    ]


def _doctor_meta(doctor_id: str) -> dict | None:
    for docs in DOCTORS_BY_DEPT.values():
        for d in docs:
            if d["id"] == doctor_id:
                return d
    return None


def _doctor_crm(doctor_id: str) -> str:
    meta = _doctor_meta(doctor_id)
    return meta["crm"] if meta else (doctor_id or "")


def _doctor_title(doctor_id: str) -> str:
    meta = _doctor_meta(doctor_id)
    return meta["title"] if meta else (doctor_id or "—")


def _base_slots(department_id: str, doctor_id: str) -> list[str]:
    if doctor_id == "movva_srinivas":
        return list(MOVVA_SLOTS)
    if department_id == "general_medicine" or doctor_id in (
        "nithin_katragadda",
        "tanoj_batchu",
    ):
        return list(GENERAL_MED_SLOTS)
    return list(DEFAULT_SLOTS)


def _day_after_tomorrow_working() -> date:
    day = datetime.now(IST).date() + timedelta(days=2)
    if day.weekday() == 6:
        day += timedelta(days=1)
    return day


def _upcoming_dates_for_doctor(doctor_id: str, days: int = 14) -> list[dict]:
    if doctor_id == "mukharjee":
        day = _day_after_tomorrow_working()
        return [{"id": day.isoformat(), "title": day.strftime("%a %d %b %Y")}]

    today = datetime.now(IST).date()
    out = []
    for offset in range(0, days + 10):
        day = today + timedelta(days=offset)
        if day.weekday() == 6:
            continue
        out.append({"id": day.isoformat(), "title": day.strftime("%a %d %b %Y")})
        if len(out) >= days:
            break
    return out


def _times_for(department_id: str, doctor_id: str, date_id: str) -> list[dict]:
    slots = _base_slots(department_id, doctor_id)
    if not date_id:
        return _slot_options(slots)

    try:
        chosen = date.fromisoformat(date_id)
    except ValueError:
        return _slot_options(slots)

    today = datetime.now(IST).date()
    if chosen != today:
        return _slot_options(slots)

    cutoff = datetime.now(IST) + timedelta(hours=2)
    filtered = []
    for label in slots:
        slot_dt = datetime.combine(chosen, _parse_slot(label), tzinfo=IST)
        if slot_dt >= cutoff:
            filtered.append(label)
    return _slot_options(filtered)


def _ensure_option(options: list[dict], option_id: str, title: str = "") -> list[dict]:
    """Keep a previously selected id in the list so Meta does not crash the Flow."""
    if not option_id:
        return options
    if any(item["id"] == option_id for item in options):
        return options
    return [{"id": option_id, "title": title or option_id}] + options


def _appointment_screen(
    department: str = "",
    doctor: str = "",
    date_id: str = "",
    time: str = "",
    *,
    form_doctor: str = "",
    form_date: str = "",
    form_time: str = "",
) -> dict:
    """Build APPOINTMENT data.

    Important (Meta Flows): never remove a currently-selected dropdown id from
    data-source — that throws "Selected id is not in options" and leaves
    Doctor/Date/Time stuck disabled / optional.
    """
    # While disabled (no dept yet), still return a real non-empty doctor list
    # like Meta's appointment template (they keep full location options).
    allowed = _doctors_for(department) if department else _doctors_for("cardiology")
    if not allowed:
        allowed = [{"id": "unavailable", "title": "No doctors available"}]

    allowed_ids = {d["id"] for d in allowed}
    doctor_ok = bool(doctor) and doctor in allowed_ids

    doctors = list(allowed)
    # Preserve whatever the WhatsApp client still has selected in the form
    for candidate in (doctor, form_doctor):
        if candidate and candidate not in {d["id"] for d in doctors}:
            meta = _doctor_meta(candidate)
            doctors = _ensure_option(
                doctors, candidate, meta["title"] if meta else candidate
            )

    date_doctor = doctor if doctor_ok else ""
    dates = _upcoming_dates_for_doctor(date_doctor)
    date_ok = bool(date_id) and any(d["id"] == date_id for d in dates)
    for candidate in (date_id, form_date):
        dates = _ensure_option(dates, candidate)

    if department and doctor_ok and date_ok:
        times = _times_for(department, doctor, date_id)
    else:
        times = _slot_options(DEFAULT_SLOTS)
    for candidate in (time, form_time):
        times = _ensure_option(times, candidate)

    return {
        "screen": "APPOINTMENT",
        "data": {
            "department": DEPARTMENTS,
            "doctor": doctors,
            "date": dates,
            "time": times,
            "is_doctor_enabled": bool(department),
            "is_date_enabled": bool(department) and doctor_ok,
            "is_time_enabled": bool(department) and doctor_ok and date_ok,
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

    if action == "ping":
        return {"version": version, "data": {"status": "active"}}

    if data.get("error"):
        return {"version": version, "data": {"acknowledged": True}}

    if action == "INIT":
        payload = _appointment_screen()
        payload["data"]["is_doctor_enabled"] = False
        payload["data"]["is_date_enabled"] = False
        payload["data"]["is_time_enabled"] = False
        payload["version"] = version
        return payload

    if action != "data_exchange":
        raise ValueError(f"Unhandled action: {action}")

    if screen == "APPOINTMENT":
        department = str(data.get("department") or "").strip()
        doctor = str(data.get("doctor") or "").strip()
        date_id = str(data.get("date") or "").strip()
        time = str(data.get("time") or "").strip()
        trigger = str(data.get("trigger") or "").strip()

        # Keep form values so we can leave their ids in data-source (Meta requirement)
        form_doctor, form_date, form_time = doctor, date_id, time

        # Parent field changed → children not "chosen" yet for enable flags
        if trigger == "department_selected":
            doctor = date_id = time = ""
        elif trigger == "doctor_selected":
            date_id = time = ""
        elif trigger == "date_selected":
            time = ""

        response = _appointment_screen(
            department,
            doctor,
            date_id,
            time,
            form_doctor=form_doctor,
            form_date=form_date,
            form_time=form_time,
        )
        response["version"] = version
        return response

    if screen == "DETAILS":
        department = str(data.get("department") or "")
        doctor = str(data.get("doctor") or "")
        date_id = str(data.get("date") or "")
        time = str(data.get("time") or "")
        name = str(data.get("name") or "").strip()
        phone = str(data.get("phone") or "").strip()
        more = str(data.get("more_details") or "").strip()

        dept_title = DEPT_TITLE.get(department, department)
        doc_title = _doctor_title(doctor)
        date_title = (
            _find_title(_upcoming_dates_for_doctor(doctor, 21), date_id)
            if date_id
            else date_id
        )

        appointment = (
            f"{dept_title} · {doc_title}\n"
            f"{DEFAULT_LOCATION_TITLE}\n"
            f"{date_title} at {time}"
        )
        details = f"Name: {name}\nPhone: {phone}"
        if more:
            details += f'\n"{more}"'

        return {
            "version": version,
            "screen": "SUMMARY",
            "data": {
                "appointment": appointment,
                "details": details,
                "department": department,
                "doctor": doctor,
                "date": date_id,
                "time": time,
                "name": name,
                "phone": phone,
                "more_details": more,
            },
        }

    if screen == "SUMMARY":
        name = str(data.get("name") or "").strip()
        phone = str(data.get("phone") or "").strip()
        department = str(data.get("department") or "")
        doctor = str(data.get("doctor") or "")
        date_id = str(data.get("date") or "")
        time = str(data.get("time") or "")
        more = str(data.get("more_details") or "").strip()

        if not name or not phone:
            return {
                "version": version,
                "screen": "DETAILS",
                "data": {
                    "error_message": "Name and phone are required.",
                    "department": department,
                    "doctor": doctor,
                    "date": date_id,
                    "time": time,
                    "name": name,
                    "phone": phone,
                    "more_details": more,
                },
            }

        try:
            db.create(
                {
                    "name": name,
                    "phone": phone,
                    "email": "",
                    "department": DEPT_CRM.get(
                        department, DEPT_TITLE.get(department, department)
                    ),
                    "doctor": _doctor_crm(doctor),
                    "preferred_date": date_id,
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
                    "doctor": doctor,
                    "date": date_id,
                    "time": time,
                    "name": name,
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
                        "doctor": _doctor_title(doctor),
                        "date": date_id,
                        "time": time,
                    }
                }
            },
        }

    if screen == "TERMS":
        return {"version": version, "screen": "TERMS", "data": {}}

    raise ValueError(f"Unhandled screen: {screen}")
