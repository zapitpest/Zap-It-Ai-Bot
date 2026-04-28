"""
GorillaDesk pest control software API client.

Reference data only — never overwrite SM8 records from GorillaDesk data.
Use for: customer lookup, job history review, invoice status cross-referencing.

API: https://app.gorilladesk.com/api/v1/
Auth: Bearer token (GORILLADESK_API_KEY from .env)
"""

import logging
import requests
from config import GORILLADESK_API_KEY

logger = logging.getLogger(__name__)

GD_BASE = "https://app.gorilladesk.com/api/v1"
GD_HEADERS = {
    "Authorization": f"Bearer {GORILLADESK_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def _get(endpoint: str, params: dict = None) -> dict:
    r = requests.get(
        f"{GD_BASE}/{endpoint}", headers=GD_HEADERS,
        params=params or {}, timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _post(endpoint: str, data: dict) -> dict:
    r = requests.post(
        f"{GD_BASE}/{endpoint}", headers=GD_HEADERS,
        json=data, timeout=15,
    )
    r.raise_for_status()
    return r.json()


# --- Customers ---

def list_customers(page: int = 1, per_page: int = 50) -> dict:
    """Returns paginated result: {data: [...], meta: {total, page, ...}}"""
    return _get("customers", {"page": page, "per_page": per_page})


def search_customers(query: str) -> list:
    """Search by name, email, or phone. Returns list of customer dicts."""
    return _get("customers", {"search": query}).get("data", [])


def get_customer(customer_id: str) -> dict:
    return _get(f"customers/{customer_id}").get("data", {})


# --- Jobs ---

def list_jobs(
    customer_id: str = None,
    status: str = None,
    page: int = 1,
) -> dict:
    """
    List jobs with optional filters.
    status: 'scheduled' | 'completed' | 'cancelled'
    """
    params: dict = {"page": page}
    if customer_id:
        params["customer_id"] = customer_id
    if status:
        params["status"] = status
    return _get("jobs", params)


def get_job(job_id: str) -> dict:
    return _get(f"jobs/{job_id}").get("data", {})


def get_completed_jobs(customer_id: str = None) -> list:
    return list_jobs(customer_id=customer_id, status="completed").get("data", [])


# --- Invoices ---

def list_invoices(
    customer_id: str = None,
    status: str = None,
    page: int = 1,
) -> dict:
    """
    List invoices with optional filters.
    status: 'draft' | 'sent' | 'paid' | 'overdue'
    """
    params: dict = {"page": page}
    if customer_id:
        params["customer_id"] = customer_id
    if status:
        params["status"] = status
    return _get("invoices", params)


def get_invoice(invoice_id: str) -> dict:
    return _get(f"invoices/{invoice_id}").get("data", {})


def get_overdue_invoices() -> list:
    return list_invoices(status="overdue").get("data", [])


def get_unpaid_invoices() -> list:
    return list_invoices(status="sent").get("data", [])


# --- Subscriptions / Recurring Services ---

def list_subscriptions(customer_id: str = None) -> list:
    params = {}
    if customer_id:
        params["customer_id"] = customer_id
    return _get("subscriptions", params).get("data", [])


# --- Service Catalogue ---

def list_services() -> list:
    """Return all service types available in GorillaDesk."""
    return _get("services").get("data", [])
