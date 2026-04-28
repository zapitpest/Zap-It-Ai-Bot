"""
Email Auto-Responder — runs every hour.

Checks for new emails and auto-responds to work orders from real estate
companies. Skips calendar invites, marketing emails, and hipages leads.
Tracks which thread IDs have already been responded to avoid duplicates.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta

from utils.gmail_client import search_emails, send_work_order_response, send_email
from utils.email_classifier import (
    is_real_estate, is_skip, is_work_order, extract_address, extract_sender_name,
)
from utils import ai_client
from utils import manus_client
from config import BUSINESS_EMAIL

logger = logging.getLogger(__name__)

RESPONDED_FILE = "responded_threads.json"


def _load_responded() -> set:
    if os.path.exists(RESPONDED_FILE):
        with open(RESPONDED_FILE) as f:
            return set(json.load(f))
    return set()


def _save_responded(thread_ids: set) -> None:
    with open(RESPONDED_FILE, "w") as f:
        json.dump(list(thread_ids), f, indent=2)


def run() -> None:
    logger.info("Running email auto-responder check")

    responded = _load_responded()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    after_str = cutoff.strftime("%Y/%m/%d")
    query = f"to:{BUSINESS_EMAIL} after:{after_str} -from:{BUSINESS_EMAIL}"

    emails = search_emails(query, max_results=50)

    newly_responded = 0
    for email in emails:
        thread_id = email.get("threadId") or email.get("id", "")

        if thread_id in responded:
            continue

        if is_skip(email):
            logger.debug("Skipping email (marketing/hipages/calendar): %s",
                         email.get("subject"))
            continue

        if not is_real_estate(email):
            continue

        if not is_work_order(email):
            continue

        body = email.get("body", email.get("snippet", ""))
        address = extract_address(body) or "the property"
        sender_name = extract_sender_name(email)
        sender_email = _parse_email_address(email.get("from", ""))
        company_name = _parse_display_name(email.get("from", ""))

        if not sender_email:
            logger.warning("Could not parse sender address from: %s", email.get("from"))
            continue

        try:
            # Try Manus first (uses learned style preferences), then Claude, then template
            ai_body = manus_client.suggest_email_response(
                sender_name=sender_name,
                property_address=address,
                company_name=company_name,
            )
            if not ai_body:
                ai_body = ai_client.generate_work_order_response(
                    sender_name=sender_name,
                    property_address=address,
                    company_name=company_name,
                )
            if ai_body:
                content = f"Hi {sender_name},<br><br>{ai_body}<br><br>Kind regards,"
                send_email(sender_email, f"Work Order Received — {address}", content)
                logger.info("Sent AI-generated response to %s re: %s", sender_email, address)
            else:
                send_work_order_response(sender_email, sender_name, address)
                logger.info("Sent template response to %s re: %s", sender_email, address)

            responded.add(thread_id)
            newly_responded += 1
        except Exception as exc:
            logger.error("Failed to send auto-response to %s: %s", sender_email, exc)

    if newly_responded:
        _save_responded(responded)

    logger.info("Auto-responder complete. %d new responses sent.", newly_responded)


def _parse_email_address(from_str: str) -> str:
    import re
    match = re.search(r"<([^>]+)>", from_str)
    if match:
        return match.group(1)
    if "@" in from_str:
        return from_str.strip()
    return ""


def _parse_display_name(from_str: str) -> str:
    """Extract the display name (company/person) from a From header."""
    import re
    match = re.match(r'^"?([^"<]+)"?\s*<', from_str)
    if match:
        return match.group(1).strip()
    return ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
