"""Pulse Heart WhatsApp appointment Flow screen logic (Meta Appointment booking template)."""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

import db

IST = ZoneInfo("Asia/Kolkata")

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

LOCATIONS = [
    {"id": "miyapur", "title": "Pulse Heart · Miyapur"},
]

DEPT_TITLE = {item["id"]: item["title"] for item in DEPARTMENTS}
LOC_TITLE = {item["id"]: item["title"] for item in LOCATIONS}

DEPT_CRM = {
    "cardiology": "Cardiology",
    "neurology": "Neurology",
    "pulmonology": "Pulmonology",
    "gastroenterology": "Gastroenterology",
    "orthopedics": "Orthopedics",
    "general_medicine": "Internal Medicine",
    "radiology": "Radiology & Imaging",
}

# id → short title (≤30) + CRM full name. Slot rules in SLOT_RULES.
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

# Default OP half-hour slots (matches doctor marketing pages).
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


def _doctor_crm(doctor_id: str) -> str:
    for docs in DOCTORS_BY_DEPT.values():
        for d in docs:
            if d["id"] == doctor_id:
                return d["crm"]
    return doctor_id or ""


def _doctor_title(doctor_id: str) -> str:
    for docs in DOCTORS_BY_DEPT.values():
        for d in docs:
            if d["id"] == doctor_id:
                return d["title"]
    return doctor_id or "—"


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
    """Mukharjee: only day-after-tomorrow; if Sunday, use Monday."""
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

    # Other doctors: only slots at least 2 hours from now (today).
    # Mukharjee never books today (date list is day-after-tomorrow only).
    cutoff = datetime.now(IST) + timedelta(hours=2)
    filtered = []
    for label in slots:
        slot_dt = datetime.combine(chosen, _parse_slot(label), tzinfo=IST)
        if slot_dt >= cutoff:
            filtered.append(label)
    return _slot_options(filtered)


def _appointment_screen(
    department: str = "",
    doctor: str = "",
    location: str = "",
    date_id: str = "",
    time: str = "",
) -> dict:
    doctors = _doctors_for(department) if department else []
    dates = (
        _upcoming_dates_for_doctor(doctor)
        if doctor
        else _upcoming_dates_for_doctor("")
    )
    times = (
        _times_for(department, doctor, date_id)
        if department and doctor and date_id
        else _times_for(department or "cardiology", doctor or "", "")
    )
    return {
        "screen": "APPOINTMENT",
        "data": {
            "department": DEPARTMENTS,
            "doctor": doctors or [{"id": "_", "title": "Select department first"}],
            "location": LOCATIONS,
            "date": dates,
            "time": times or [{"id": "_", "title": "No slots available"}],
            "is_doctor_enabled": bool(department),
            "is_location_enabled": bool(department) and bool(doctor),
            "is_date_enabled": bool(department) and bool(doctor) and bool(location),
            "is_time_enabled": bool(department)
            and bool(doctor)
            and bool(location)
            and bool(date_id),
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
        payload["data"]["is_location_enabled"] = False
        payload["data"]["is_date_enabled"] = False
        payload["data"]["is_time_enabled"] = False
        payload["version"] = version
        return payload

    if action != "data_exchange":
        raise ValueError(f"Unhandled action: {action}")

    if screen == "APPOINTMENT":
        department = str(data.get("department") or "")
        doctor = str(data.get("doctor") or "")
        location = str(data.get("location") or "")
        date_id = str(data.get("date") or "")
        time = str(data.get("time") or "")
        # Reset dependent fields when parent changes mid-cascade
        if not department:
            doctor = location = date_id = time = ""
        elif doctor and doctor not in {d["id"] for d in _doctors_for(department)}:
            doctor = location = date_id = time = ""
        response = _appointment_screen(department, doctor, location, date_id, time)
        response["version"] = version
        return response

    if screen == "DETAILS":
        department = str(data.get("department") or "")
        doctor = str(data.get("doctor") or "")
        location = str(data.get("location") or "")
        date_id = str(data.get("date") or "")
        time = str(data.get("time") or "")
        name = str(data.get("name") or "").strip()
        email = str(data.get("email") or "").strip()
        phone = str(data.get("phone") or "").strip()
        more = str(data.get("more_details") or "").strip()

        dept_title = DEPT_TITLE.get(department, department)
        loc_title = LOC_TITLE.get(location, location)
        doc_title = _doctor_title(doctor)
        date_title = _find_title(_upcoming_dates_for_doctor(doctor, 21), date_id) if date_id else date_id

        appointment = (
            f"{dept_title} · {doc_title}\n"
            f"at {loc_title}\n"
            f"{date_title} at {time}"
        )
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
                "doctor": doctor,
                "location": location,
                "date": date_id,
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
                    **{
                        k: data.get(k, "")
                        for k in (
                            "department",
                            "doctor",
                            "location",
                            "date",
                            "time",
                            "name",
                            "email",
                            "phone",
                            "more_details",
                        )
                    },
                },
            }

        try:
            db.create(
                {
                    "name": name,
                    "phone": phone,
                    "email": email,
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
                    "location": data.get("location") or "",
                    "date": date_id,
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
