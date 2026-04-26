"""
Afternoon Email Summary — runs at 5:00 PM daily.
Scans Gmail for all emails since 7:00 AM that morning.
Same format as the morning summary.
"""

import logging
from datetime import datetime, timedelta, timezone

from utils.gmail_client import search_emails, send_email
from utils.email_classifier import is_real_estate, is_skip, is_work_order
from config import BUSINESS_EMAIL

logger = logging.getLogger(__name__)


def _format_email_line(email: dict, prefix: str = "") -> str:
    subject = email.get("subject", "(no subject)")
    sender = email.get("from", "unknown")
    snippet = email.get("snippet", "")[:120]
    return f"{prefix}<b>{subject}</b> | From: {sender}<br><i>{snippet}</i>"


def run() -> None:
    logger.info("Running afternoon email summary")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=10)
    after_str = cutoff.strftime("%Y/%m/%d")
    query = f"to:{BUSINESS_EMAIL} after:{after_str} -from:{BUSINESS_EMAIL}"

    emails = search_emails(query, max_results=100)

    real_estate_work_orders = []
    other_emails = []

    for email in emails:
        if is_skip(email):
            continue
        if is_real_estate(email) and is_work_order(email):
            real_estate_work_orders.append(email)
        else:
            other_emails.append(email)

    lines = ["<h2>Afternoon Email Summary</h2>",
             f"<p>Emails received since 7:00 AM today ({len(emails)} total, "
             f"{len(real_estate_work_orders)} work orders flagged)</p>"]

    if real_estate_work_orders:
        lines.append("<h3>Real Estate Work Orders — ACTION REQUIRED</h3><ul>")
        for e in real_estate_work_orders:
            lines.append(f"<li>{_format_email_line(e, '&#x26A0;&#xFE0F; ')}</li>")
        lines.append("</ul>")

    if other_emails:
        lines.append("<h3>Other Emails</h3><ul>")
        for e in other_emails:
            lines.append(f"<li>{_format_email_line(e)}</li>")
        lines.append("</ul>")

    if not real_estate_work_orders and not other_emails:
        lines.append("<p>No new emails requiring attention.</p>")

    content = "\n".join(lines)
    send_email(
        to=BUSINESS_EMAIL,
        subject=f"Afternoon Summary — {datetime.now().strftime('%a %d %b %Y')}",
        content=content,
    )
    logger.info("Afternoon summary sent (%d emails processed)", len(emails))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
