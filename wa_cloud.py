"""WhatsApp Cloud API helpers — menu replies, Flow launch, location, confirmation."""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import requests

log = logging.getLogger("pulse-desk.wa")

GRAPH = "https://graph.facebook.com/v21.0"

# Pulse Heart · Miyapur (maps embed)
HOSPITAL_LAT = 17.49612568334056
HOSPITAL_LNG = 78.3643976102618
HOSPITAL_NAME = "Pulse Heart Super Speciality Hospital"
HOSPITAL_ADDRESS = (
    "Pillar No.605, Mumbai Highway, Mathrusree Nagar, Miyapur, Hyderabad - 500049"
)
APPOINTMENTS_PHONE = "8886688063"
EMERGENCY_PHONE = "9000777019"


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _phone_id() -> str:
    return _env("WA_PHONE_NUMBER_ID")


def _token() -> str:
    return _env("WA_ACCESS_TOKEN")


def normalize_wa_to(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0") and len(digits) == 11:
        digits = "91" + digits[1:]
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def send_graph(payload: dict[str, Any]) -> dict[str, Any] | None:
    phone_id = _phone_id()
    token = _token()
    if not phone_id or not token:
        log.warning("WA_PHONE_NUMBER_ID / WA_ACCESS_TOKEN missing — skip send")
        return None
    url = f"{GRAPH}/{phone_id}/messages"
    try:
        res = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        data = res.json() if res.content else {}
        if res.status_code >= 400:
            log.error("WA send failed %s %s", res.status_code, data)
            return None
        return data
    except Exception:
        log.exception("WA send error")
        return None


def send_text(to: str, body: str) -> dict | None:
    to = normalize_wa_to(to)
    if not to or not body:
        return None
    return send_graph(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body[:4096]},
        }
    )


def send_main_menu(to: str) -> dict | None:
    """Reply menu: Book / Emergency / Location."""
    to = normalize_wa_to(to)
    return send_graph(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {"type": "text", "text": "Pulse Heart · Miyapur"},
                "body": {
                    "text": (
                        "Welcome to Pulse Heart Super Speciality Hospital.\n"
                        "How can we help you?"
                    )
                },
                "footer": {"text": "OP Mon–Sat · Sun closed"},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": "menu_book", "title": "Book appointment"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": "menu_emergency", "title": "Emergency"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": "menu_location", "title": "Location"},
                        },
                    ]
                },
            },
        }
    )


def send_location(to: str) -> dict | None:
    to = normalize_wa_to(to)
    return send_graph(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "location",
            "location": {
                "latitude": HOSPITAL_LAT,
                "longitude": HOSPITAL_LNG,
                "name": HOSPITAL_NAME,
                "address": HOSPITAL_ADDRESS,
            },
        }
    )


def send_emergency(to: str) -> dict | None:
    emergency = _env("WA_EMERGENCY_PHONE", EMERGENCY_PHONE)
    appt = _env("WA_APPOINTMENTS_PHONE", APPOINTMENTS_PHONE)
    body = (
        "🚨 Pulse Heart Emergency\n\n"
        f"Emergency: +91 {emergency}\n"
        f"Appointments: +91 {appt}\n\n"
        "If this is life-threatening, call emergency now or come to the hospital immediately.\n"
        f"{HOSPITAL_ADDRESS}"
    )
    result = send_text(to, body)
    send_location(to)
    return result


def send_flow(to: str, flow_token: str = "") -> dict | None:
    """Open the published appointment Flow. Requires WA_FLOW_ID after Publish."""
    flow_id = _env("WA_FLOW_ID")
    to = normalize_wa_to(to)
    if not flow_id:
        log.warning("WA_FLOW_ID not set — send book instructions instead")
        return send_text(
            to,
            "To book an appointment, please reply again after our booking Flow is published, "
            f"or call +91 {APPOINTMENTS_PHONE}.",
        )
    token = flow_token or to
    return send_graph(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "flow",
                "header": {"type": "text", "text": "Book appointment"},
                "body": {
                    "text": (
                        "Choose department, doctor, date and time. "
                        "Our desk will confirm shortly."
                    )
                },
                "footer": {"text": "Pulse Heart · Miyapur"},
                "action": {
                    "name": "flow",
                    "parameters": {
                        "flow_message_version": "3",
                        "flow_token": token,
                        "flow_id": flow_id,
                        "flow_cta": "Book now",
                        "flow_action": "data_exchange",
                    },
                },
            },
        }
    )


def send_booking_confirmation(
    to: str,
    *,
    name: str,
    department: str,
    doctor: str,
    date_label: str,
    time_label: str,
) -> dict | None:
    body = (
        "✅ Appointment request received\n\n"
        f"Name: {name}\n"
        f"Department: {department}\n"
        f"Doctor: {doctor}\n"
        f"Date: {date_label}\n"
        f"Time: {time_label}\n"
        f"Place: {HOSPITAL_NAME}, Miyapur\n\n"
        "Our front desk will call or WhatsApp you to confirm the slot.\n"
        f"Help: +91 {APPOINTMENTS_PHONE}"
    )
    return send_text(to, body)


def handle_inbound_message(msg: dict, contacts: list | None = None) -> None:
    """Process one inbound WhatsApp message object."""
    from_id = str(msg.get("from") or "")
    if not from_id:
        log.warning("WA inbound missing from")
        return

    if not _phone_id() or not _token():
        log.error(
            "Cannot reply: set WA_PHONE_NUMBER_ID and WA_ACCESS_TOKEN in .env then recreate containers"
        )
        return

    msg_type = msg.get("type")
    button_id = ""

    if msg_type == "interactive":
        interactive = msg.get("interactive") or {}
        if interactive.get("type") == "button_reply":
            button_id = str((interactive.get("button_reply") or {}).get("id") or "")
        elif interactive.get("type") == "list_reply":
            button_id = str((interactive.get("list_reply") or {}).get("id") or "")
    elif msg_type == "button":
        button_id = str((msg.get("button") or {}).get("payload") or "")

    log.info("WA handle from=%s type=%s button=%s", from_id, msg_type, button_id or "-")

    if button_id == "menu_book":
        send_flow(from_id, flow_token=from_id)
        return
    if button_id == "menu_emergency":
        send_emergency(from_id)
        return
    if button_id == "menu_location":
        send_text(
            from_id,
            f"📍 {HOSPITAL_NAME}\n{HOSPITAL_ADDRESS}\n\nTap the location pin below.",
        )
        send_location(from_id)
        return

    # Any other inbound (including button/list already handled) → main menu
    # Also reply to empty-type edge cases Meta sometimes sends
    if msg_type in (
        "text",
        "image",
        "audio",
        "video",
        "document",
        "sticker",
        "contacts",
        "location",
        "unknown",
        "interactive",
        "button",
        None,
        "",
    ):
        result = send_main_menu(from_id)
        if not result:
            log.error("WA main menu send failed for %s", from_id)
        return

    # Fallback: still send menu
    send_main_menu(from_id)
