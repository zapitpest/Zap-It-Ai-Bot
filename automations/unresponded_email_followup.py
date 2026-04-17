"""
Unresponded Email Follow-Up — runs at 7:00 AM and 7:00 PM daily.

Checks for work order emails that haven't been responded to within
a reasonable window and sends a follow-up alert to the business inbox.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone, timedelta

from utils.gmail_client import search_emails, send_email, send_followup_email
from utils.email_classifier import (
    is_real_estate, is_skip, is_work_order, extract_address, extract_sender_name,
)
from config import BUSINESS_EMAIL

logger = logging.getLogger(__name__)

RESPONDED_FILE = "responded_threads.json"
FOLLOWUP_SENT_FILE = "followup_sent.json"
UNRESPONDED_WINDOW_HOURS = 12


def _load_json_set(path: str) -> set:
    if os.path.exists(path):
        with open(path) as f:
            return set(json.load(f))
    return set()


def _save_json_set(path: str, data: set) -> None:
    with open(path, "w") as f:
        json.dump(list(data), f, indent=2)


def _parse_email_address(from_str: str) -> str:
    match = re.search(r"<([^>]+)>", from_str)
    if match:
        return match.group(1)
    if "@" in from_str:
        return from_str.strip()
    return ""


def run() -> None:
    logger.info("Running unresponded email follow-up check")

    responded = _load_json_set(RESPONDED_FILE)
    followup_sent = _load_json_set(FOLLOWUP_SENT_FILE)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=UNRESPONDED_WINDOW_HOURS)
    after_str = cutoff.strftime("%Y/%m/%d")
    query = f"to:{BUSINESS_EMAIL} after:{after_str} -from:{BUSINESS_EMAIL}"

    emails = search_emails(query, max_results=100)

    unresponded = []
    for email in emails:
        thread_id = email.get("threadId") or email.get("id", "")
        if is_skip(email):
            continue
        if not is_real_estate(email) or not is_work_order(email):
            continue
        if thread_id in responded:
            continue
        unresponded.append(email)

    if not unresponded:
        logger.info("No unresponded work orders found.")
        return

    # Send internal alert summary
    alert_lines = [
        "<h2>Unresponded Work Orders Alert</h2>",
        f"<p>The following {len(unresponded)} work order(s) have not been responded "
        f"to within {UNRESPONDED_WINDOW_HOURS} hours:</p><ul>",
    ]
    for email in unresponded:
        subject = email.get("subject", "(no subject)")
        sender = email.get("from", "unknown")
        snippet = email.get("snippet", "")[:120]
        alert_lines.append(
            f"<li><b>{subject}</b><br>From: {sender}<br><i>{snippet}</i></li>"
        )
    alert_lines.append("</ul>")

    send_email(
        to=BUSINESS_EMAIL,
        subject=f"ACTION REQUIRED: {len(unresponded)} Unresponded Work Order(s)",
        content="\n".join(alert_lines),
    )
    logger.info("Sent alert for %d unresponded work orders", len(unresponded))

    # Send follow-up to each unresponded sender if not already followed up
    new_followups = 0
    for email in unresponded:
        thread_id = email.get("threadId") or email.get("id", "")
        if thread_id in followup_sent:
            continue

        body = email.get("body", email.get("snippet", ""))
        address = extract_address(body) or "the property"
        sender_name = extract_sender_name(email)
        sender_email = _parse_email_address(email.get("from", ""))

        if not sender_email:
            continue

        try:
            send_followup_email(sender_email, sender_name, address)
            followup_sent.add(thread_id)
            new_followups += 1
            logger.info("Sent follow-up to %s re: %s", sender_email, address)
        except Exception as exc:
            logger.error("Failed to send follow-up to %s: %s", sender_email, exc)

    if new_followups:
        _save_json_set(FOLLOWUP_SENT_FILE, followup_sent)

    logger.info("Follow-up complete. %d new follow-ups sent.", new_followups)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
