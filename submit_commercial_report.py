"""
Commercial Report Submission Pipeline.

Strict 6-step process:
  1. Google Sheet update (last service date, invoice info)
  2. ServiceM8 job creation
  3. Add invoice line items
  4. Mark job as Completed
  5. Send invoice email
  6. Send report email

Only process jobs the user explicitly lists. Never auto-process all
commercial clients. Always confirm the job list, activity levels, and
exceptions before starting.

Client exceptions:
  - Sanagweech: skip entirely
  - Donatellos: invoice only, no report

Default low-activity report wording:
  "Low activity found at time of inspection. Area was found clean and tidy
   at time of inspection. Recommend to maintain high levels of hygiene and
   sanitation to prevent pest activity."
"""

import logging
from datetime import datetime, timezone

import utils.servicem8_client as sm8
from utils.gmail_client import send_invoice_email, send_report_email
from utils.google_sheets_client import (
    find_client_by_name,
    update_last_service_date,
    update_invoice_info,
)
from config import COMMERCIAL_REPORT_URL

logger = logging.getLogger(__name__)

LOW_ACTIVITY_WORDING = (
    "Low activity found at time of inspection. Area was found clean and tidy "
    "at time of inspection. Recommend to maintain high levels of hygiene and "
    "sanitation to prevent pest activity."
)

SKIP_CLIENTS = {"sanagweech"}
INVOICE_ONLY_CLIENTS = {"donatellos"}


def _normalise_name(name: str) -> str:
    return name.strip().lower()


class JobSpec:
    """Represents one commercial job to process."""

    def __init__(
        self,
        business_name: str,
        address: str,
        contact_name: str,
        contact_email: str,
        charge_ex_gst: float,
        tax_rate_uuid: str = "",
        report_notes: str = LOW_ACTIVITY_WORDING,
        report_url: str = "",
        service_date: str = "",
        technician_uuid: str = "",
        skip_report: bool = False,
    ):
        self.business_name = business_name
        self.address = address
        self.contact_name = contact_name
        self.contact_email = contact_email
        self.charge_ex_gst = charge_ex_gst
        self.tax_rate_uuid = tax_rate_uuid
        self.report_notes = report_notes
        self.report_url = report_url or COMMERCIAL_REPORT_URL
        self.service_date = service_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.technician_uuid = technician_uuid
        self.skip_report = skip_report


def process_job(spec: JobSpec) -> dict:
    """
    Execute the 6-step pipeline for a single commercial job.
    Returns a summary dict with step results.
    """
    bname_key = _normalise_name(spec.business_name)
    results = {}

    # Guard: skip specific clients
    if bname_key in SKIP_CLIENTS:
        logger.info("Skipping '%s' — on skip list", spec.business_name)
        return {"skipped": True, "reason": "on skip list"}

    invoice_only = bname_key in INVOICE_ONLY_CLIENTS

    # Step 1: Google Sheet update
    logger.info("[1/6] Updating Google Sheet for '%s'", spec.business_name)
    try:
        client_row = find_client_by_name(spec.business_name)
        if client_row:
            update_last_service_date(client_row["row_index"], spec.service_date)
            results["sheet_update"] = "ok"
        else:
            logger.warning("No sheet row found for '%s'", spec.business_name)
            results["sheet_update"] = "not_found"
    except Exception as exc:
        logger.error("Sheet update failed: %s", exc)
        results["sheet_update"] = f"error: {exc}"

    # Step 2: Create SM8 job
    logger.info("[2/6] Creating SM8 job for '%s'", spec.business_name)
    try:
        company = _find_or_create_company(spec)
        job = sm8.create_job(
            company_uuid=company["uuid"],
            status="Work Order",
            description=f"Commercial pest control service at {spec.address}",
            geo_street=spec.address,
        )
        job_uuid = job["uuid"]
        results["job_uuid"] = job_uuid
        logger.info("Created SM8 job %s", job_uuid)
    except Exception as exc:
        logger.error("SM8 job creation failed: %s", exc)
        results["job_creation"] = f"error: {exc}"
        return results

    # Step 3: Add invoice line items
    logger.info("[3/6] Adding line items for '%s'", spec.business_name)
    try:
        sm8.add_material(
            job_uuid=job_uuid,
            name="Commercial Pest Control Service",
            quantity=1,
            price=spec.charge_ex_gst,
            tax_rate_uuid=spec.tax_rate_uuid,
        )
        results["line_items"] = "ok"
    except Exception as exc:
        logger.error("Line item creation failed: %s", exc)
        results["line_items"] = f"error: {exc}"

    # Step 4: Mark job as Completed
    logger.info("[4/6] Marking SM8 job %s as Completed", job_uuid)
    try:
        sm8.complete_job(job_uuid)
        results["job_completed"] = "ok"
    except Exception as exc:
        logger.error("Failed to mark job complete: %s", exc)
        results["job_completed"] = f"error: {exc}"

    # Step 5: Send invoice email
    logger.info("[5/6] Sending invoice email for '%s'", spec.business_name)
    try:
        send_invoice_email(spec.contact_email, spec.contact_name, spec.address)
        results["invoice_sent"] = "ok"
        # Update sheet with invoice status
        if client_row:
            update_invoice_info(
                client_row["row_index"],
                invoice_number=job_uuid[:8].upper(),
                amount_owing=str(spec.charge_ex_gst),
                date_str=spec.service_date,
                status="Sent",
            )
    except Exception as exc:
        logger.error("Invoice email failed: %s", exc)
        results["invoice_sent"] = f"error: {exc}"

    # Step 6: Send report email (skip for invoice-only clients)
    if invoice_only or spec.skip_report:
        logger.info("[6/6] Skipping report for '%s' (invoice only)", spec.business_name)
        results["report_sent"] = "skipped"
    else:
        logger.info("[6/6] Sending report email for '%s'", spec.business_name)
        try:
            send_report_email(
                spec.contact_email, spec.contact_name, spec.address, spec.report_url
            )
            results["report_sent"] = "ok"
        except Exception as exc:
            logger.error("Report email failed: %s", exc)
            results["report_sent"] = f"error: {exc}"

    logger.info("Pipeline complete for '%s': %s", spec.business_name, results)
    return results


def _find_or_create_company(spec: JobSpec) -> dict:
    """Find an existing SM8 company by name or create a new one."""
    companies = sm8.get_companies()
    name_lower = spec.business_name.strip().lower()
    for company in companies:
        if company.get("name", "").strip().lower() == name_lower:
            return company
    return sm8.create_company(spec.business_name, spec.address)


def run_batch(job_specs: list[JobSpec]) -> list[dict]:
    """Process a list of JobSpec objects and return all results."""
    all_results = []
    for spec in job_specs:
        result = process_job(spec)
        result["business_name"] = spec.business_name
        all_results.append(result)
    return all_results


if __name__ == "__main__":
    import argparse
    import json
    logging.basicConfig(level=logging.INFO)
    print("submit_commercial_report.py — run via the scheduler or import run_batch()")
    print("To process jobs, construct JobSpec objects and call run_batch(job_specs)")
