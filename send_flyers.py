"""
Treatment Flyer Automation — triggered after completed jobs.

Rules:
  Residential : ALWAYS send the matched flyer.
  Commercial / Real Estate : ONLY send for specific treatments
    (wasps, moths, rodents, bed bugs, possums, ants).
    Skip if it's a general spray.

Duplicate prevention via flyers_sent.json (keyed by job UUID + flyer key).
"""

import json
import logging
import os
import re

import utils.servicem8_client as sm8
from utils.gmail_client import send_flyer_email
from config import (
    FLYERS_SENT_FILE,
    FLYER_URL_MAP,
    FLYER_GENERAL,
    COMMERCIAL_FLYER_TREATMENTS,
)

logger = logging.getLogger(__name__)

COMMERCIAL_TYPE_KEYWORDS = [
    "real estate", "property", "realty", "leasing", "rental",
    "restaurant", "cafe", "office", "facility", "childcare",
    "hotel", "motel", "warehouse", "factory", "retail",
]

TREATMENT_KEYWORD_MAP = {
    "cockroach": "cockroach",
    "cockroaches": "cockroach",
    "roach": "cockroach",
    "wasp": "wasp",
    "wasps": "wasp",
    "bee": "wasp",
    "bees": "wasp",
    "moth": "moth",
    "moths": "moth",
    "rodent": "rodent",
    "rodents": "rodent",
    "rat": "rodent",
    "rats": "rodent",
    "mouse": "rodent",
    "mice": "rodent",
    "bed bug": "bed bug",
    "bed bugs": "bed bug",
    "bedbug": "bed bug",
    "bedbugs": "bed bug",
    "possum": "possum",
    "possums": "possum",
    "ant": "ant",
    "ants": "ant",
    "termite": "termite",
    "termites": "termite",
    "flea": "flea",
    "fleas": "flea",
    "spider": "spider",
    "spiders": "spider",
    "general": "general",
    "general spray": "general",
    "general pest": "general",
}


def _load_sent() -> dict:
    if os.path.exists(FLYERS_SENT_FILE):
        with open(FLYERS_SENT_FILE) as f:
            return json.load(f)
    return {}


def _save_sent(data: dict) -> None:
    with open(FLYERS_SENT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _extract_treatment(text: str) -> str:
    """Return the first matched treatment keyword from the text."""
    text_lower = text.lower()
    for keyword, treatment in TREATMENT_KEYWORD_MAP.items():
        if keyword in text_lower:
            return treatment
    return "general"


def _is_commercial(job: dict) -> bool:
    """
    Determine if a job is commercial/real estate.
    Check company name and job description for commercial indicators.
    """
    try:
        company = sm8.get_company(job.get("company_uuid", ""))
        company_name = company.get("name", "").lower()
    except Exception:
        company_name = ""

    desc = job.get("description", "").lower()
    combined = company_name + " " + desc

    return any(kw in combined for kw in COMMERCIAL_TYPE_KEYWORDS)


def _get_flyer_url(treatment: str) -> str:
    """Map treatment name to a flyer URL. Fall back to general flyer."""
    return FLYER_URL_MAP.get(treatment, FLYER_GENERAL)


def _get_client_email(job: dict) -> tuple[str, str]:
    """Return (email, contact_name) for the job's client."""
    try:
        contacts = sm8.get_job_contacts(job["uuid"])
        if contacts:
            c = contacts[0]
            first = c.get("first_name", "")
            last = c.get("last_name", "")
            email = c.get("email", "")
            name = f"{first} {last}".strip() or "there"
            if email:
                return email, name
    except Exception:
        pass

    # Fallback: company contact
    try:
        company_contacts = sm8.get_contacts(job.get("company_uuid", ""))
        if company_contacts:
            c = company_contacts[0]
            first = c.get("first_name", "")
            last = c.get("last_name", "")
            email = c.get("email", "")
            name = f"{first} {last}".strip() or "there"
            if email:
                return email, name
    except Exception:
        pass

    return "", ""


def process_job(job: dict, sent_log: dict) -> bool:
    """
    Evaluate one completed job and send a flyer if rules are met.
    Returns True if a flyer was sent.
    """
    job_uuid = job.get("uuid", "")
    description = job.get("description", "")
    address = " ".join(filter(None, [
        job.get("geo_street", ""),
        job.get("geo_suburb", ""),
        job.get("geo_state", ""),
    ])) or "the property"

    # Extract materials text for better treatment detection
    try:
        materials = sm8.get_materials(job_uuid)
        materials_text = " ".join(m.get("name", "") for m in materials)
    except Exception:
        materials_text = ""

    full_text = f"{description} {materials_text}"
    treatment = _extract_treatment(full_text)
    flyer_key = f"{job_uuid}:{treatment}"

    # Skip if already sent
    if flyer_key in sent_log:
        logger.debug("Flyer already sent for job %s (%s)", job_uuid, treatment)
        return False

    is_commercial = _is_commercial(job)

    # Apply commercial rule: only specific treatments get flyers
    if is_commercial:
        treatment_words = set(re.split(r"\s+", treatment))
        if not (treatment_words & COMMERCIAL_FLYER_TREATMENTS):
            logger.info(
                "Skipping flyer for commercial job %s — treatment '%s' not in allowed list",
                job_uuid, treatment,
            )
            return False

    email, contact_name = _get_client_email(job)
    if not email:
        logger.warning("No email found for job %s — skipping flyer", job_uuid)
        return False

    flyer_url = _get_flyer_url(treatment)

    try:
        send_flyer_email(email, contact_name, address, treatment, flyer_url)
        sent_log[flyer_key] = {
            "job_uuid": job_uuid,
            "treatment": treatment,
            "email": email,
            "address": address,
            "is_commercial": is_commercial,
        }
        logger.info(
            "Sent %s flyer for job %s to %s (commercial=%s)",
            treatment, job_uuid, email, is_commercial,
        )
        return True
    except Exception as exc:
        logger.error("Failed to send flyer for job %s: %s", job_uuid, exc)
        return False


def run(hours: int = 24) -> None:
    """
    Main entry point. Fetches completed jobs from the last `hours` hours
    and sends appropriate flyers.
    """
    logger.info("Running treatment flyer automation (last %d hours)", hours)

    try:
        jobs = sm8.get_completed_jobs_since(hours=hours)
    except Exception as exc:
        logger.error("Failed to fetch completed jobs: %s", exc)
        return

    logger.info("Found %d completed jobs to evaluate", len(jobs))

    sent_log = _load_sent()
    sent_count = 0

    for job in jobs:
        if process_job(job, sent_log):
            sent_count += 1

    if sent_count:
        _save_sent(sent_log)

    logger.info("Flyer automation complete. %d flyers sent.", sent_count)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Send treatment flyers for completed jobs")
    parser.add_argument("--hours", type=int, default=24,
                        help="How many hours back to check for completed jobs")
    args = parser.parse_args()
    run(hours=args.hours)
