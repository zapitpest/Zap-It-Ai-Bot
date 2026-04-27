"""
CRM Sync — runs daily at 9:00 AM.

Fetches all ServiceM8 companies that have a primary contact email and
upserts them into GoHighLevel CRM. Adds a service note with the SM8 UUID
for cross-referencing. Skips companies with no email on any contact.
"""

import logging
from datetime import datetime, timezone

import utils.servicem8_client as sm8
from utils.gohighlevel_client import upsert_contact, add_note

logger = logging.getLogger(__name__)


def run() -> None:
    logger.info("Running CRM sync: ServiceM8 → GoHighLevel")

    try:
        companies = sm8.get_companies()
    except Exception as exc:
        logger.error("Could not fetch SM8 companies: %s", exc)
        return

    synced = 0
    skipped = 0

    for company in companies:
        name = (company.get("name") or "").strip()
        if not name:
            skipped += 1
            continue

        company_uuid = company.get("uuid", "")

        # Find a contact with an email address
        primary_email = ""
        primary_name = ""
        primary_phone = ""
        try:
            contacts = sm8.get_contacts(company_uuid)
            for contact in contacts:
                if contact.get("email"):
                    primary_email = contact["email"]
                    first = contact.get("first", "") or ""
                    last = contact.get("last", "") or ""
                    primary_name = f"{first} {last}".strip() or name
                    primary_phone = (
                        contact.get("mobile_phone", "")
                        or contact.get("work_phone", "")
                        or ""
                    )
                    break
        except Exception as exc:
            logger.warning("Could not fetch contacts for '%s': %s", name, exc)

        if not primary_email:
            logger.debug("No email for '%s' — skipping GHL sync", name)
            skipped += 1
            continue

        try:
            contact = upsert_contact(
                email=primary_email,
                name=primary_name,
                phone=primary_phone,
                tags=["pest-control-client", "servicem8"],
            )
            contact_id = contact.get("id", "")
            if contact_id:
                add_note(
                    contact_id,
                    f"ServiceM8 company: {name}\n"
                    f"SM8 UUID: {company_uuid}\n"
                    f"Last synced: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                )
            synced += 1
            logger.info("Synced '%s' → GHL (contact: %s)", name, contact_id)
        except Exception as exc:
            logger.error("GHL sync failed for '%s': %s", name, exc)

    logger.info("CRM sync complete — synced: %d, skipped: %d", synced, skipped)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
