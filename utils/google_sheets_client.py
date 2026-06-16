"""Google Sheets client using the gws CLI tool.

The commercial clients sheet ID: 1dDZdZ01d5MjdwYkfwxHgNvFisa1wQL_ReWZYR6RJZ7o
Tab: "Commercial Clients"

Column mapping (0-indexed):
 A=0  Client ID
 B=1  Business Name
 C=2  Service Frequency
 D=3  Business Type
 E=4  Contact Person
 F=5  Phone
 G=6  Email
 H=7  Service Address
 I=8  Suburb
 J=9  Custom Frequency Notes
 K=10 Last Service Date
 L=11 Next Service Due Date
 M=12 Last Invoice Date
 N=13 Technician Assigned
 O=14 Charge Per Service ex GST
 P=15 Annual Value ex GST
 Q=16 Latest Invoice Number
 R=17 Amount Owing ex GST
 S=18 Payment Status
 T=19 Days Overdue
 U=20 Priority
 V=21 Access Instructions
 W=22 Site Notes
 X=23 Last Follow-Up Date
 Y=24 Next Follow-Up Date
 Z=25 Missed Service Flag
"""

import json
import subprocess
from config import COMMERCIAL_SHEET_ID, COMMERCIAL_SHEET_TAB

COL = {
    "client_id": 0,
    "business_name": 1,
    "frequency": 2,
    "business_type": 3,
    "contact_person": 4,
    "phone": 5,
    "email": 6,
    "address": 7,
    "suburb": 8,
    "frequency_notes": 9,
    "last_service_date": 10,
    "next_service_due": 11,
    "last_invoice_date": 12,
    "technician": 13,
    "charge_ex_gst": 14,
    "annual_value": 15,
    "invoice_number": 16,
    "amount_owing": 17,
    "payment_status": 18,
    "days_overdue": 19,
    "priority": 20,
    "access_instructions": 21,
    "site_notes": 22,
    "last_followup_date": 23,
    "next_followup_date": 24,
    "missed_service_flag": 25,
}


def _gws(args: list) -> str:
    result = subprocess.run(
        ["gws"] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gws error: {result.stderr}")
    return result.stdout.strip()


def read_sheet(sheet_id: str = COMMERCIAL_SHEET_ID,
               tab: str = COMMERCIAL_SHEET_TAB,
               range_: str = "A:Z") -> list[list]:
    """Return all rows as a list of lists (raw string values)."""
    raw = _gws(["read", sheet_id, f"'{tab}'!{range_}"])
    return json.loads(raw) if raw else []


def update_cell(row: int, col_letter: str, value: str,
                sheet_id: str = COMMERCIAL_SHEET_ID,
                tab: str = COMMERCIAL_SHEET_TAB) -> None:
    """Update a single cell. row is 1-indexed."""
    cell = f"'{tab}'!{col_letter}{row}"
    _gws(["write", sheet_id, cell, value])


def update_row_cells(row_index: int, updates: dict,
                     sheet_id: str = COMMERCIAL_SHEET_ID,
                     tab: str = COMMERCIAL_SHEET_TAB) -> None:
    """
    Update multiple cells in a row.
    updates: { col_letter: value, ... }
    row_index: 1-based row number (header is row 1, first data row is 2).
    """
    for col_letter, value in updates.items():
        update_cell(row_index, col_letter, str(value), sheet_id, tab)


def get_commercial_clients() -> list[dict]:
    """Return all commercial client rows as a list of dicts."""
    rows = read_sheet()
    if not rows:
        return []
    header = rows[0]
    clients = []
    for i, row in enumerate(rows[1:], start=2):
        padded = row + [""] * (26 - len(row))
        clients.append({
            "row_index": i,
            "client_id": padded[COL["client_id"]],
            "business_name": padded[COL["business_name"]],
            "frequency": padded[COL["frequency"]],
            "business_type": padded[COL["business_type"]],
            "contact_person": padded[COL["contact_person"]],
            "phone": padded[COL["phone"]],
            "email": padded[COL["email"]],
            "address": padded[COL["address"]],
            "suburb": padded[COL["suburb"]],
            "frequency_notes": padded[COL["frequency_notes"]],
            "last_service_date": padded[COL["last_service_date"]],
            "next_service_due": padded[COL["next_service_due"]],
            "last_invoice_date": padded[COL["last_invoice_date"]],
            "technician": padded[COL["technician"]],
            "charge_ex_gst": padded[COL["charge_ex_gst"]],
            "annual_value": padded[COL["annual_value"]],
            "invoice_number": padded[COL["invoice_number"]],
            "amount_owing": padded[COL["amount_owing"]],
            "payment_status": padded[COL["payment_status"]],
            "days_overdue": padded[COL["days_overdue"]],
            "priority": padded[COL["priority"]],
            "access_instructions": padded[COL["access_instructions"]],
            "site_notes": padded[COL["site_notes"]],
            "last_followup_date": padded[COL["last_followup_date"]],
            "next_followup_date": padded[COL["next_followup_date"]],
            "missed_service_flag": padded[COL["missed_service_flag"]],
        })
    return clients


def find_client_by_name(name: str) -> dict | None:
    """Case-insensitive search by business name."""
    name_lower = name.strip().lower()
    for client in get_commercial_clients():
        if client["business_name"].strip().lower() == name_lower:
            return client
    return None


def find_client_by_address(address: str, suburb: str = "") -> dict | None:
    """Match by address fragment and optional suburb."""
    address_lower = address.strip().lower()
    suburb_lower = suburb.strip().lower()
    for client in get_commercial_clients():
        if address_lower in client["address"].strip().lower():
            if not suburb_lower or suburb_lower in client["suburb"].strip().lower():
                return client
    return None


def update_last_service_date(row_index: int, date_str: str) -> None:
    """date_str: 'YYYY-MM-DD'"""
    update_cell(row_index, "K", date_str)


def update_payment_status(row_index: int, status: str) -> None:
    """status: 'Paid' | 'Draft' | 'Sent'"""
    update_cell(row_index, "S", status)


def update_invoice_info(row_index: int, invoice_number: str,
                        amount_owing: str, date_str: str,
                        status: str = "Sent") -> None:
    update_row_cells(row_index, {
        "Q": invoice_number,
        "R": amount_owing,
        "M": date_str,
        "S": status,
    })
