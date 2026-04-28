"""
Meta Ads Lead Sync — runs every 30 minutes.

Fetches new lead form submissions from Facebook/Instagram ad campaigns
and for each new lead:
  1. Upserts a contact in GoHighLevel CRM
  2. Creates a ServiceM8 job (status: Quote)
  3. Sends a welcome/follow-up email via Gmail
  4. Tracks processed lead IDs in meta_leads_seen.json to avoid duplicates
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import utils.servicem8_client as sm8
from utils.gmail_client import send_email
from utils.gohighlevel_client import upsert_contact, add_note
from utils import meta_ads_client as meta
from config import BUSINESS_NAME, BUSINESS_EMAIL

logger = logging.getLogger(__name__)

SEEN_FILE = Path("meta_leads_seen.json")


def _load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def _save_seen(seen: set) -> None:
    SEEN_FILE.write_text(json.dumps(list(seen), indent=2))


def _send_welcome_email(email: str, name: str) -> None:
    first = (name or "there").split()[0]
    content = (
        f"Hi {first},<br><br>"
        f"Thanks for your enquiry with {BUSINESS_NAME}! "
        f"We've received your details and one of our team will be in touch shortly "
        f"to arrange a time that suits you.<br><br>"
        f"In the meantime, if you have any urgent questions please call us on "
        f"03 9126 0555.<br><br>"
        f"Kind regards,"
    )
    send_email(email, "Thanks for your enquiry — Zap It Pest Control", content)


def run() -> None:
    logger.info("Running Meta Ads lead sync")

    seen = _load_seen()
    new_count = 0

    try:
        ad_account = meta.get_account()
        account_id = ad_account.get("id", "")
        logger.info("Meta account: %s (%s)", ad_account.get("name", ""), account_id)
    except Exception as exc:
        logger.error("Could not connect to Meta Ads API: %s", exc)
        return

    # Get all active lead forms across the account
    try:
        forms = meta.list_lead_forms()
    except Exception as exc:
        logger.error("Could not fetch lead forms: %s", exc)
        return

    if not forms:
        logger.info("No lead forms found on this account")
        return

    logger.info("Found %d lead form(s)", len(forms))

    for form in forms:
        form_id = form.get("id", "")
        form_name = form.get("name", "unknown form")

        try:
            leads = meta.get_leads(form_id, limit=50)
        except Exception as exc:
            logger.warning("Could not fetch leads for form '%s': %s", form_name, exc)
            continue

        for lead in leads:
            lead_id = lead.get("id", "")
            if not lead_id or lead_id in seen:
                continue

            parsed = meta.parse_lead(lead)
            name = (
                parsed.get("full_name")
                or f"{parsed.get('first_name', '')} {parsed.get('last_name', '')}".strip()
                or "Unknown"
            )
            email = parsed.get("email", "")
            phone = parsed.get("phone_number", "") or parsed.get("phone", "")
            address = parsed.get("address", "") or parsed.get("street_address", "")
            pest_type = parsed.get("pest_type", "") or parsed.get("service_type", "")
            created = lead.get("created_time", "")

            logger.info(
                "New lead from '%s': %s <%s> (created: %s)",
                form_name, name, email, created,
            )

            # 1. GoHighLevel CRM
            if email:
                try:
                    contact = upsert_contact(
                        email=email,
                        name=name,
                        phone=phone,
                        address=address,
                        tags=["meta-ads-lead", "pest-control-enquiry"],
                    )
                    contact_id = contact.get("id", "")
                    if contact_id:
                        add_note(
                            contact_id,
                            f"Lead source: Meta Ads — {form_name}\n"
                            f"Pest type: {pest_type or 'not specified'}\n"
                            f"Submitted: {created}\n"
                            f"Lead ID: {lead_id}",
                        )
                    logger.info("GHL contact upserted: %s", contact_id)
                except Exception as exc:
                    logger.error("GHL upsert failed for lead %s: %s", lead_id, exc)

            # 2. ServiceM8 quote job
            try:
                companies = sm8.get_companies()
                company = None
                name_lower = name.strip().lower()
                for c in companies:
                    if c.get("name", "").strip().lower() == name_lower:
                        company = c
                        break

                if not company:
                    company = sm8.create_company(name, address or "")

                description = f"Meta Ads enquiry — {pest_type or 'pest control'}"
                if address:
                    description += f" at {address}"

                job = sm8.create_job(
                    company_uuid=company["uuid"],
                    status="Quote",
                    description=description,
                    geo_street=address or "",
                )
                logger.info("SM8 quote job created: %s", job.get("uuid", ""))
            except Exception as exc:
                logger.error("SM8 job creation failed for lead %s: %s", lead_id, exc)

            # 3. Welcome email
            if email:
                try:
                    _send_welcome_email(email, name)
                    logger.info("Welcome email sent to %s", email)
                except Exception as exc:
                    logger.error("Welcome email failed for %s: %s", email, exc)

            seen.add(lead_id)
            new_count += 1

    if new_count:
        _save_seen(seen)

    logger.info("Meta lead sync complete — %d new lead(s) processed", new_count)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
