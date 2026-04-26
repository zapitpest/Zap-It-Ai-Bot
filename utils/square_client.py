"""Square API client for bookings and customer data.

IMPORTANT: Square does NOT support personal/non-billable events via API.
For non-billable tasks the AI must find the best time and give details
to the user to add manually in the Square app.
"""

import requests
from config import SQUARE_BASE_URL, SQUARE_HEADERS


def _url(path: str) -> str:
    return f"{SQUARE_BASE_URL}/{path.lstrip('/')}"


def get(path: str, params: dict = None) -> dict:
    resp = requests.get(_url(path), headers=SQUARE_HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def post(path: str, data: dict) -> dict:
    resp = requests.post(_url(path), headers=SQUARE_HEADERS, json=data)
    resp.raise_for_status()
    return resp.json()


# --- Customers ---

def get_customers(cursor: str = None) -> dict:
    params = {}
    if cursor:
        params["cursor"] = cursor
    return get("customers", params)


def get_all_customers() -> list:
    customers = []
    cursor = None
    while True:
        resp = get_customers(cursor)
        customers.extend(resp.get("customers", []))
        cursor = resp.get("cursor")
        if not cursor:
            break
    return customers


def search_customers(query: str) -> list:
    data = {
        "query": {
            "filter": {
                "email_address": {"fuzzy": query}
            }
        }
    }
    resp = post("customers/search", data)
    return resp.get("customers", [])


# --- Bookings ---

def create_booking(customer_id: str, location_id: str, start_at: str,
                   service_variation_id: str, team_member_id: str,
                   duration_minutes: int = 60,
                   service_variation_version: int = 1) -> dict:
    """
    Creates a booking for a PAID service only.
    start_at must be RFC 3339: '2026-04-25T09:00:00+10:00'
    """
    data = {
        "booking": {
            "start_at": start_at,
            "location_id": location_id,
            "customer_id": customer_id,
            "appointment_segments": [
                {
                    "duration_minutes": duration_minutes,
                    "service_variation_id": service_variation_id,
                    "team_member_id": team_member_id,
                    "service_variation_version": service_variation_version,
                }
            ],
        }
    }
    return post("bookings", data)


def get_bookings(location_id: str = None, start_at: str = None,
                 end_at: str = None) -> list:
    params = {}
    if location_id:
        params["location_id"] = location_id
    if start_at:
        params["start_at_min"] = start_at
    if end_at:
        params["start_at_max"] = end_at
    resp = get("bookings", params)
    return resp.get("bookings", [])


def get_booking(booking_id: str) -> dict:
    return get(f"bookings/{booking_id}")


def cancel_booking(booking_id: str, version: int) -> dict:
    data = {"booking_version": version}
    resp = requests.post(
        _url(f"bookings/{booking_id}/cancel"),
        headers=SQUARE_HEADERS,
        json=data,
    )
    resp.raise_for_status()
    return resp.json()


# --- Locations ---

def get_locations() -> list:
    resp = get("locations")
    return resp.get("locations", [])


# --- Team Members ---

def get_team_members(location_id: str = None) -> list:
    params = {}
    if location_id:
        params["location_ids[]"] = location_id
    resp = get("team-members/search", {})
    return resp.get("team_members", [])


# --- Catalog / Services ---

def get_catalog_items(types: str = "ITEM") -> list:
    params = {"types": types}
    resp = get("catalog/list", params)
    return resp.get("objects", [])
