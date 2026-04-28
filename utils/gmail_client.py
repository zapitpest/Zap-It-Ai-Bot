"""
Gmail client — three-layer fallback:
  1. mcp_gmail native module (when running inside Claude Code / Manus MCP)
  2. manus-mcp-cli subprocess (legacy Manus agent environment)
  3. Direct Gmail API via Google OAuth (standalone — run setup_google_auth.py first)
"""

import base64
import json
import logging
import subprocess
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    BUSINESS_EMAIL, BUSINESS_NAME, BUSINESS_PHONE,
    LOGO_GREEN_BG, SIGNATURE_NAME,
)

logger = logging.getLogger(__name__)

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


def _gmail_service():
    """Build and return an authenticated Gmail API service."""
    from googleapiclient.discovery import build
    from utils.google_oauth import get_credentials
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


def send_email(to: str | list, subject: str, content: str, html: bool = True) -> dict:
    """Send email. Tries MCP → manus-mcp-cli → direct Gmail API."""
    recipients = [to] if isinstance(to, str) else to
    full_content = content + EMAIL_SIGNATURE_HTML if html else content

    # Layer 1: native MCP module
    try:
        from mcp_gmail import send as mcp_send
        return mcp_send(recipients, subject, full_content)
    except ImportError:
        pass

    # Layer 2: manus-mcp-cli subprocess
    try:
        result = subprocess.run(
            ["manus-mcp-cli", "tool", "call", "gmail_send_messages", "-s", "gmail"],
            input=json.dumps({"messages": [{"to": recipients, "subject": subject,
                                            "content": full_content}]}),
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except FileNotFoundError:
        pass
    except Exception as exc:
        logger.warning("manus-mcp-cli send failed: %s", exc)

    # Layer 3: direct Gmail API
    logger.debug("Using direct Gmail API to send email")
    service = _gmail_service()
    msg = MIMEMultipart("alternative")
    msg["To"] = ", ".join(recipients)
    msg["From"] = BUSINESS_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(full_content, "html" if html else "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info("Email sent via Gmail API (id: %s)", sent.get("id"))
    return sent


def search_emails(query: str, max_results: int = 50) -> list:
    """Search Gmail. Tries MCP → manus-mcp-cli → direct Gmail API."""

    # Layer 1: native MCP module
    try:
        from mcp_gmail import search as mcp_search
        return mcp_search(query, max_results)
    except ImportError:
        pass

    # Layer 2: manus-mcp-cli subprocess
    try:
        result = subprocess.run(
            ["manus-mcp-cli", "tool", "call", "gmail_search_messages", "-s", "gmail"],
            input=json.dumps({"query": query, "max_results": max_results}),
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout).get("messages", [])
    except FileNotFoundError:
        pass
    except Exception as exc:
        logger.warning("manus-mcp-cli search failed: %s", exc)

    # Layer 3: direct Gmail API
    logger.debug("Using direct Gmail API to search emails")
    service = _gmail_service()
    resp = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = []
    for item in resp.get("messages", []):
        msg = service.users().messages().get(
            userId="me", messageId=item["id"], format="full"
        ).execute()
        messages.append(_parse_message(msg))

    return messages


def _parse_message(msg: dict) -> dict:
    """Convert raw Gmail API message to the flat dict format the bot uses."""
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    body = _extract_body(msg.get("payload", {}))
    return {
        "id": msg.get("id", ""),
        "threadId": msg.get("threadId", ""),
        "subject": headers.get("Subject", ""),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "body": body,
    }


def _extract_body(payload: dict) -> str:
    """Recursively extract plain-text or HTML body from a Gmail payload."""
    mime = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data", "")

    if data and mime in ("text/plain", "text/html"):
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return ""


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
