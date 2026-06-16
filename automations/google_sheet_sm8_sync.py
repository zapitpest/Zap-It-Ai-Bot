"""
Google Sheet <-> ServiceM8 Sync — runs at 8:00 PM on Mon/Wed/Fri.

Checks ServiceM8 for completed commercial jobs in the last 48 hours.
Matches them to Google Sheet rows by business name, address, and suburb.
Updates 'Last Service Date' (col K) and 'Payment Status' (col S) on the
Commercial Clients tab.

GorillaDesk data is used for reference ONLY — never overwrite SM8 data
with GorillaDesk data blindly.
"""

import logging
from datetime import datetime, timezone, timedelta

import utils.servicem8_client as sm8
from utils.google_sheets_client import (
    get_commercial_clients,
    find_client_by_name,
    find_client_by_address,
    update_last_service_date,
    update_payment_status,
)

logger = logging.getLogger(__name__)

SYNC_WINDOW_HOURS = 48


def _normalise(s: str) -> str:
    return s.strip().lower()


def _match_job_to_client(job: dict, clients: list[dict]) -> dict | None:
    """Try to find a Google Sheet client matching this SM8 job."""
    job_company_uuid = job.get("company_uuid", "")
    job_desc = _normalise(job.get("description", ""))
    job_address = _normalise(job.get("geo_street", "") + " " + job.get("geo_suburb", ""))

    # Try to fetch the company name from SM8
    try:
        company = sm8.get_company(job_company_uuid)
        company_name = company.get("name", "")
    except Exception:
        company_name = ""

    if company_name:
        client = find_client_by_name(company_name)
        if client:
            return client

    # Fallback: match by address
    if job.get("geo_street"):
        client = find_client_by_address(job["geo_street"], job.get("geo_suburb", ""))
        if client:
            return client

    # Fallback: fuzzy name match from description
    for client in clients:
        bname = _normalise(client["business_name"])
        if bname and bname in job_desc:
            return client

    return None


def run() -> None:
    logger.info("Running Google Sheet <-> ServiceM8 sync")

    try:
        clients = get_commercial_clients()
    except Exception as exc:
        logger.error("Failed to fetch commercial clients from sheet: %s", exc)
        return

    try:
        completed_jobs = sm8.get_completed_jobs_since(hours=SYNC_WINDOW_HOURS)
    except Exception as exc:
        logger.error("Failed to fetch completed SM8 jobs: %s", exc)
        return

    logger.info("Checking %d completed SM8 jobs against %d sheet clients",
                len(completed_jobs), len(clients))

    updated = 0
    for job in completed_jobs:
        client = _match_job_to_client(job, clients)
        if not client:
            logger.debug("No sheet match for job %s", job.get("uuid"))
            continue

        completion_date = (
            job.get("completion_date")
            or job.get("edit_date", "")[:10]
        )
        if not completion_date:
            completion_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        try:
            update_last_service_date(client["row_index"], completion_date)
            logger.info(
                "Updated last service date for '%s' (row %d) -> %s",
                client["business_name"], client["row_index"], completion_date,
            )
            updated += 1
        except Exception as exc:
            logger.error(
                "Failed to update sheet row %d for '%s': %s",
                client["row_index"], client["business_name"], exc,
            )

    logger.info("Sync complete. %d rows updated.", updated)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
