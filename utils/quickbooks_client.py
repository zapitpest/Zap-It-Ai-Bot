"""
QuickBooks Online API client.

Requires one-time OAuth 2.0 setup before use. Run the auth flow once:
  python -m utils.quickbooks_client --auth

This opens a browser, completes the Intuit OAuth flow, and saves tokens
to .qb_tokens.json. The client then auto-refreshes tokens as needed.

Required .env vars:
  QUICKBOOKS_CLIENT_ID      — from developer.intuit.com app dashboard
  QUICKBOOKS_CLIENT_SECRET  — from developer.intuit.com app dashboard
  QUICKBOOKS_REALM_ID       — Company ID, printed after --auth completes

The existing QUICKBOOKS_API_KEY env var is not used by this client;
QuickBooks does not support simple API key auth.
"""

import json
import logging
import os
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

QB_BASE = "https://quickbooks.api.intuit.com/v3/company"
QB_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QB_AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
QB_SCOPE = "com.intuit.quickbooks.accounting"
QB_TOKEN_FILE = Path(".qb_tokens.json")
QB_MINOR_VER = "65"

CLIENT_ID = os.environ.get("QUICKBOOKS_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("QUICKBOOKS_CLIENT_SECRET", "")
REALM_ID = os.environ.get("QUICKBOOKS_REALM_ID", "")


def _load_tokens() -> dict:
    if QB_TOKEN_FILE.exists():
        return json.loads(QB_TOKEN_FILE.read_text())
    return {}


def _save_tokens(tokens: dict) -> None:
    QB_TOKEN_FILE.write_text(json.dumps(tokens, indent=2))


def _refresh(refresh_token: str) -> dict:
    r = requests.post(
        QB_TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=15,
    )
    r.raise_for_status()
    tokens = r.json()
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600) - 60
    _save_tokens(tokens)
    return tokens


def _access_token() -> str:
    tokens = _load_tokens()
    if not tokens:
        raise RuntimeError(
            "QuickBooks not authenticated. "
            "Run: python -m utils.quickbooks_client --auth"
        )
    if time.time() > tokens.get("expires_at", 0):
        tokens = _refresh(tokens["refresh_token"])
    return tokens["access_token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_access_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _realm() -> str:
    realm = REALM_ID or _load_tokens().get("realm_id", "")
    if not realm:
        raise RuntimeError("QUICKBOOKS_REALM_ID not set. Run --auth first.")
    return realm


def _get(path: str, params: dict = None) -> dict:
    r = requests.get(
        f"{QB_BASE}/{_realm()}/{path}",
        headers=_headers(),
        params={"minorversion": QB_MINOR_VER, **(params or {})},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def query(sql: str) -> list:
    """Run a QuickBooks query-language SELECT. Returns a flat list of results."""
    r = requests.get(
        f"{QB_BASE}/{_realm()}/query",
        headers=_headers(),
        params={"query": sql, "minorversion": QB_MINOR_VER},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json().get("QueryResponse", {})
    for value in data.values():
        if isinstance(value, list):
            return value
    return []


# --- Invoices ---

def get_invoice(invoice_id: str) -> dict:
    return _get(f"invoice/{invoice_id}").get("Invoice", {})


def list_unpaid_invoices(max_results: int = 100) -> list:
    return query(f"SELECT * FROM Invoice WHERE Balance > '0' MAXRESULTS {max_results}")


def list_overdue_invoices(max_results: int = 100) -> list:
    from datetime import date
    today = date.today().isoformat()
    return query(
        f"SELECT * FROM Invoice WHERE Balance > '0' AND DueDate < '{today}' "
        f"MAXRESULTS {max_results}"
    )


# --- Customers ---

def get_customer(customer_id: str) -> dict:
    return _get(f"customer/{customer_id}").get("Customer", {})


def list_customers(active_only: bool = True, max_results: int = 100) -> list:
    where = "WHERE Active = true " if active_only else ""
    return query(f"SELECT * FROM Customer {where}MAXRESULTS {max_results}")


def search_customer_by_name(name: str, max_results: int = 10) -> list:
    safe = name.replace("'", "\\'")
    return query(
        f"SELECT * FROM Customer WHERE DisplayName LIKE '%{safe}%' MAXRESULTS {max_results}"
    )


# --- Payments ---

def list_payments(customer_id: str = None, max_results: int = 100) -> list:
    if customer_id:
        return query(
            f"SELECT * FROM Payment WHERE CustomerRef = '{customer_id}' "
            f"MAXRESULTS {max_results}"
        )
    return query(f"SELECT * FROM Payment MAXRESULTS {max_results}")


def get_payment(payment_id: str) -> dict:
    return _get(f"payment/{payment_id}").get("Payment", {})


# --- OAuth2 Setup CLI ---

if __name__ == "__main__":
    import argparse
    import webbrowser
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs, urlencode, urlparse

    parser = argparse.ArgumentParser(description="QuickBooks OAuth2 setup")
    parser.add_argument("--auth", action="store_true", help="Run OAuth2 flow")
    args = parser.parse_args()

    if not args.auth:
        print("Run with --auth to complete QuickBooks OAuth2 setup.")
        raise SystemExit(0)

    if not CLIENT_ID or not CLIENT_SECRET:
        print("Set QUICKBOOKS_CLIENT_ID and QUICKBOOKS_CLIENT_SECRET in .env first.")
        raise SystemExit(1)

    auth_url = QB_AUTH_URL + "?" + urlencode({
        "client_id": CLIENT_ID,
        "scope": QB_SCOPE,
        "redirect_uri": "http://localhost:8080/callback",
        "response_type": "code",
        "state": "zapitbot",
    })
    print(f"Opening browser for QuickBooks authorisation...\n{auth_url}\n")
    webbrowser.open(auth_url)

    _holder: dict = {}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            qs = parse_qs(urlparse(self.path).query)
            _holder["code"] = qs.get("code", [""])[0]
            _holder["realm_id"] = qs.get("realmId", [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>QuickBooks auth complete. You can close this tab.</h2>")

        def log_message(self, *_):
            pass

    HTTPServer(("localhost", 8080), _Handler).handle_request()

    r = requests.post(
        QB_TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": _holder["code"],
            "redirect_uri": "http://localhost:8080/callback",
        },
        timeout=15,
    )
    tokens = r.json()
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600) - 60
    tokens["realm_id"] = _holder["realm_id"]
    _save_tokens(tokens)

    print(f"Tokens saved to {QB_TOKEN_FILE}")
    print(f"Add this to your .env:  QUICKBOOKS_REALM_ID={_holder['realm_id']}")
