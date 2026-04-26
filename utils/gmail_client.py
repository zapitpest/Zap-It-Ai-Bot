"""Gmail client using the native Gmail MCP server (mcp__69e81224).

send_email uses the create_draft + send flow via MCP tools.
search_emails uses search_threads.
"""

import subprocess
import json
from datetime import datetime, timedelta, timezone
from config import (
    BUSINESS_NAME, BUSINESS_PHONE, BUSINESS_EMAIL,
    SIGNATURE_NAME, LOGO_GREEN_BG,
)

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


def send_email(to: str | list, subject: str, content: str,
               html: bool = True) -> dict:
    """Send email via Gmail MCP. content is HTML by default."""
    recipients = [to] if isinstance(to, str) else to
    full_content = content + EMAIL_SIGNATURE_HTML if html else content
    # Invoked at runtime by the scheduler via the MCP tool directly.
    # When running inside Claude Code the MCP tool is called natively.
    # Fallback: manus-mcp-cli for standalone execution.
    try:
        from mcp_gmail import send as mcp_send
        return mcp_send(recipients, subject, full_content)
    except ImportError:
        pass
    cmd = ["manus-mcp-cli", "tool", "call", "gmail_send_messages", "-s", "gmail"]
    result = subprocess.run(
        cmd,
        input=json.dumps({"messages": [{"to": recipients, "subject": subject,
                                        "content": full_content}]}),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Gmail send error: {result.stderr}")
    return json.loads(result.stdout)


def search_emails(query: str, max_results: int = 50) -> list:
    """Search Gmail threads. Returns list of message dicts."""
    try:
        from mcp_gmail import search as mcp_search
        return mcp_search(query, max_results)
    except ImportError:
        pass
    cmd = ["manus-mcp-cli", "tool", "call", "gmail_search_messages", "-s", "gmail"]
    result = subprocess.run(
        cmd,
        input=json.dumps({"query": query, "max_results": max_results}),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Gmail search error: {result.stderr}")
    return json.loads(result.stdout).get("messages", [])


def emails_since(hours: int = 12, extra_query: str = "") -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    after_str = cutoff.strftime("%Y/%m/%d")
    query = f"after:{after_str}"
    if extra_query:
        query += f" {extra_query}"
    return search_emails(query)


# --- Named email templates ---

def send_work_order_response(to: str, contact_name: str, address: str) -> dict:
    content = f"""Hi {contact_name},<br><br>
Thank you for sending through the work order for {address}. We have received it and will contact the tenant shortly to arrange a suitable time for the treatment.<br><br>
We will keep you updated on the progress.<br><br>
Kind regards,"""
    return send_email(to, f"Work Order Received — {address}", content)


def send_invoice_email(to: str, contact_name: str, address: str,
                       attachment_url: str = "") -> dict:
    content = f"""Hi {contact_name},<br><br>
Please find attached the invoice for the pest control service completed at {address}.<br><br>
Payment can be made via Bank Deposit, Card, or online payment. Our bank details are:<br>
Account Name: Prime Solutions Group<br>
BSB: 033143<br>
Account Number: 649414<br><br>
Thank you for your business.<br><br>
Kind regards,"""
    return send_email(to, f"Invoice — Pest Control Service at {address}", content)


def send_report_email(to: str, contact_name: str, address: str,
                      report_url: str) -> dict:
    content = f"""Hi {contact_name},<br><br>
Please find a link to the pest control report for the service completed at {address}:<br>
<a href="{report_url}">{report_url}</a><br><br>
If you have any questions or require further assistance, please don't hesitate to contact us.<br><br>
Kind regards,"""
    return send_email(to, f"Pest Control Report — {address}", content)


def send_followup_email(to: str, contact_name: str, address: str) -> dict:
    content = f"""Hi {contact_name},<br><br>
Just following up on the work order for {address}. We have tried contacting the tenant but haven't been able to reach them.<br><br>
Could you please assist in arranging access or provide an alternative contact number?<br><br>
Kind regards,"""
    return send_email(to, f"Follow-Up — Work Order at {address}", content)


def send_flyer_email(to: str, contact_name: str, address: str,
                     treatment_type: str, flyer_url: str) -> dict:
    content = f"""Hi {contact_name},<br><br>
Thank you for choosing {BUSINESS_NAME} for your recent {treatment_type} treatment at {address}.<br><br>
We have put together a brief flyer with some helpful information and aftercare tips regarding your treatment:<br>
<a href="{flyer_url}">{flyer_url}</a><br><br>
If you have any questions, please feel free to reach out.<br><br>
Kind regards,"""
    return send_email(to, f"Treatment Aftercare Info — {address}", content)
