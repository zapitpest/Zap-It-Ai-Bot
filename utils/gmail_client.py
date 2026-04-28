"""
Gmail client using SMTP (simple, no OAuth needed).

Setup (one-time):
  1. Go to https://myaccount.google.com/apppasswords
  2. Select: Mail → Windows Computer (or other)
  3. Google generates a 16-char password
  4. Add to .env: GMAIL_APP_PASSWORD=<16-char-password>
  5. Done — bot can now send/read emails

For reading: uses Gmail API if credentials exist, falls back to IMAP search.
For sending: uses SMTP (works everywhere).
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from imaplib import IMAP4_SSL
from datetime import datetime, timedelta, timezone
import os

from config import (
    BUSINESS_EMAIL, BUSINESS_NAME, BUSINESS_PHONE,
    LOGO_GREEN_BG, SIGNATURE_NAME,
)

logger = logging.getLogger(__name__)

GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

EMAIL_SIGNATURE_HTML = f"""
<br><br>
<table cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td>
      <img src="{LOGO_GREEN_BG}" alt="ZAPiT Logo" width="120" style="display:block;"/>
    </td>
    <td style="padding-left:12px;font-family:Arial,sans-serif;font-size:13px;color:#333;">
      <strong>{SIGNATURE_NAME}</strong><br>
      {BUSINESS_NAME}<br>
      {BUSINESS_PHONE}<br>
      <a href="mailto:{BUSINESS_EMAIL}" style="color:#2E7D32;">{BUSINESS_EMAIL}</a>
    </td>
  </tr>
</table>
"""


def send_email(to: str | list, subject: str, content: str, html: bool = True) -> dict:
    """Send email via Gmail SMTP. Simple and works everywhere."""
    if not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_APP_PASSWORD not set. "
            "Go to https://myaccount.google.com/apppasswords "
            "and generate a 16-char app password, then add to .env"
        )

    recipients = [to] if isinstance(to, str) else to
    full_content = content + EMAIL_SIGNATURE_HTML if html else content

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = BUSINESS_EMAIL
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(full_content, "html" if html else "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(BUSINESS_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(BUSINESS_EMAIL, recipients, msg.as_string())
        logger.info("Email sent to %s (subject: %s)", recipients[0], subject)
        return {"success": True, "message_id": subject}
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        raise


def search_emails(query: str, max_results: int = 50) -> list:
    """Search Gmail using IMAP. Returns list of message dicts."""
    if not GMAIL_APP_PASSWORD:
        logger.warning("GMAIL_APP_PASSWORD not set — cannot search emails")
        return []

    messages = []
    try:
        with IMAP4_SSL("imap.gmail.com", timeout=10) as imap:
            imap.login(BUSINESS_EMAIL, GMAIL_APP_PASSWORD)
            imap.select("INBOX")

            # Convert query to IMAP search criteria
            # Simple support for: "after:YYYY/MM/DD" and text keywords
            search_criteria = _convert_query(query)
            status, msg_ids = imap.search(None, search_criteria)

            if status != "OK":
                logger.warning("IMAP search failed: %s", status)
                return []

            msg_list = msg_ids[0].split()[-max_results:]  # Get last N results

            for msg_id in msg_list:
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status == "OK":
                    messages.append(_parse_email(msg_data[0][1]))

        logger.info("Found %d emails matching: %s", len(messages), query)
    except Exception as exc:
        logger.error("IMAP search failed: %s", exc)

    return messages


def _convert_query(query: str) -> tuple:
    """Convert Gmail query format to IMAP search criteria."""
    # Simple conversion: "after:YYYY/MM/DD" → IMAP SINCE
    # and text keywords → IMAP TEXT
    criteria = []

    if "after:" in query:
        date_str = query.split("after:")[-1].split()[0]
        try:
            criteria.append(f'SINCE "{date_str}"')
        except Exception:
            pass

    # Add text search for keywords
    keywords = [w for w in query.split() if not w.startswith("after:")]
    if keywords:
        criteria.append(f'TEXT "{" ".join(keywords)}"')

    return ("ALL",) if not criteria else tuple(criteria)


def _parse_email(raw_message: bytes) -> dict:
    """Parse raw IMAP email into a flat dict."""
    from email import message_from_bytes

    msg = message_from_bytes(raw_message)
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                break
    else:
        body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

    return {
        "id": msg.get("Message-ID", ""),
        "threadId": msg.get("In-Reply-To", ""),
        "subject": msg.get("Subject", ""),
        "from": msg.get("From", ""),
        "to": msg.get("To", ""),
        "date": msg.get("Date", ""),
        "snippet": body[:200],
        "body": body,
    }


def emails_since(hours: int = 12, extra_query: str = "") -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    after_str = cutoff.strftime("%Y/%m/%d")
    query = f"after:{after_str}"
    if extra_query:
        query += f" {extra_query}"
    return search_emails(query)


# --- Named email templates ---

def send_work_order_response(to: str, contact_name: str, address: str) -> dict:
    content = (
        f"Hi {contact_name},<br><br>"
        f"Thank you for sending through the work order for {address}. "
        f"We have received it and will contact the tenant shortly to arrange a suitable time for the treatment.<br><br>"
        f"We will keep you updated on the progress.<br><br>"
        f"Kind regards,"
    )
    return send_email(to, f"Work Order Received — {address}", content)


def send_invoice_email(to: str, contact_name: str, address: str,
                       attachment_url: str = "") -> dict:
    content = (
        f"Hi {contact_name},<br><br>"
        f"Please find attached the invoice for the pest control service completed at {address}.<br><br>"
        f"Payment can be made via Bank Deposit, Card, or online payment. Our bank details are:<br>"
        f"Account Name: Prime Solutions Group<br>"
        f"BSB: 033143<br>"
        f"Account Number: 649414<br><br>"
        f"Thank you for your business.<br><br>"
        f"Kind regards,"
    )
    return send_email(to, f"Invoice — Pest Control Service at {address}", content)


def send_report_email(to: str, contact_name: str, address: str, report_url: str) -> dict:
    content = (
        f"Hi {contact_name},<br><br>"
        f"Please find a link to the pest control report for the service completed at {address}:<br>"
        f'<a href="{report_url}">{report_url}</a><br><br>'
        f"If you have any questions or require further assistance, please don't hesitate to contact us.<br><br>"
        f"Kind regards,"
    )
    return send_email(to, f"Pest Control Report — {address}", content)


def send_followup_email(to: str, contact_name: str, address: str) -> dict:
    content = (
        f"Hi {contact_name},<br><br>"
        f"Just following up on the work order for {address}. "
        f"We have tried contacting the tenant but haven't been able to reach them.<br><br>"
        f"Could you please assist in arranging access or provide an alternative contact number?<br><br>"
        f"Kind regards,"
    )
    return send_email(to, f"Follow-Up — Work Order at {address}", content)


def send_flyer_email(to: str, contact_name: str, address: str,
                     treatment_type: str, flyer_url: str) -> dict:
    content = (
        f"Hi {contact_name},<br><br>"
        f"Thank you for choosing {BUSINESS_NAME} for your recent {treatment_type} treatment at {address}.<br><br>"
        f"We have put together a brief flyer with some helpful information and aftercare tips regarding your treatment:<br>"
        f'<a href="{flyer_url}">{flyer_url}</a><br><br>'
        f"If you have any questions, please feel free to reach out.<br><br>"
        f"Kind regards,"
    )
    return send_email(to, f"Treatment Aftercare Info — {address}", content)
