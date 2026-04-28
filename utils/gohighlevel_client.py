"""
GoHighLevel CRM API client.

Used to sync pest control clients from ServiceM8 into the GHL CRM,
create pipeline opportunities, and log service activity as contact notes.

API reference: https://rest.gohighlevel.com/
Auth: Bearer token (GOHIGHLEVEL_API_KEY from .env)
"""

import logging
import requests
from config import GOHIGHLEVEL_API_KEY

logger = logging.getLogger(__name__)

GHL_BASE = "https://rest.gohighlevel.com/v1"
GHL_HEADERS = {
    "Authorization": f"Bearer {GOHIGHLEVEL_API_KEY}",
    "Content-Type": "application/json",
}


def _get(endpoint: str, params: dict = None) -> dict:
    r = requests.get(
        f"{GHL_BASE}/{endpoint}", headers=GHL_HEADERS,
        params=params or {}, timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _post(endpoint: str, data: dict) -> dict:
    r = requests.post(
        f"{GHL_BASE}/{endpoint}", headers=GHL_HEADERS,
        json=data, timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _put(endpoint: str, data: dict) -> dict:
    r = requests.put(
        f"{GHL_BASE}/{endpoint}", headers=GHL_HEADERS,
        json=data, timeout=15,
    )
    r.raise_for_status()
    return r.json()


# --- Contacts ---

def search_contact(email: str = None, phone: str = None) -> list:
    """Search contacts by email or phone. Returns list of contact dicts."""
    params = {}
    if email:
        params["email"] = email
    if phone:
        params["phone"] = phone
    return _get("contacts/search", params).get("contacts", [])


def get_contact(contact_id: str) -> dict:
    return _get(f"contacts/{contact_id}").get("contact", {})


def create_contact(
    email: str,
    name: str,
    phone: str = "",
    address: str = "",
    tags: list = None,
) -> dict:
    """Create a new GHL contact. Returns the created contact dict."""
    parts = (name or "").split(maxsplit=1)
    data = {
        "email": email,
        "firstName": parts[0] if parts else "",
        "lastName": parts[1] if len(parts) > 1 else "",
        "tags": tags or ["pest-control-client"],
    }
    if phone:
        data["phone"] = phone
    if address:
        data["address1"] = address
    return _post("contacts", data).get("contact", {})


def upsert_contact(
    email: str,
    name: str,
    phone: str = "",
    address: str = "",
    tags: list = None,
) -> dict:
    """Return the existing contact (matched by email) or create a new one."""
    existing = search_contact(email=email)
    if existing:
        return existing[0]
    return create_contact(email, name, phone, address, tags)


def update_contact(contact_id: str, **fields) -> dict:
    return _put(f"contacts/{contact_id}", fields).get("contact", {})


def add_tags(contact_id: str, tags: list) -> dict:
    return _post(f"contacts/{contact_id}/tags", {"tags": tags})


def add_note(contact_id: str, body: str) -> dict:
    return _post(f"contacts/{contact_id}/notes", {"body": body})


# --- Opportunities / Pipeline ---

def get_pipelines() -> list:
    return _get("pipelines").get("pipelines", [])


def create_opportunity(
    contact_id: str,
    pipeline_id: str,
    stage_id: str,
    name: str,
    monetary_value: float = None,
    status: str = "open",
) -> dict:
    data = {
        "pipelineId": pipeline_id,
        "name": name,
        "pipelineStageId": stage_id,
        "contactId": contact_id,
        "status": status,
    }
    if monetary_value is not None:
        data["monetaryValue"] = monetary_value
    return _post("opportunities", data)


def update_opportunity(opportunity_id: str, **fields) -> dict:
    return _put(f"opportunities/{opportunity_id}", fields)


# --- Conversations / SMS ---

def get_conversations(contact_id: str) -> list:
    return _get("conversations/search", {"contactId": contact_id}).get("conversations", [])


def send_sms(contact_id: str, message: str) -> dict:
    return _post("conversations/messages", {
        "type": "SMS",
        "contactId": contact_id,
        "message": message,
    })
