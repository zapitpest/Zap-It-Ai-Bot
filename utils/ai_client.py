"""
AI client for email intelligence using Anthropic Claude.

Uses Claude Haiku for fast/cheap classification and response generation.
Degrades gracefully to empty returns if ANTHROPIC_API_KEY is not set or
the SDK call fails — callers are responsible for falling back to keyword logic.
"""

import json
import logging
from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except Exception as exc:
        logger.warning("Could not initialise Anthropic client: %s", exc)
    return _client


def classify_email(subject: str, body: str, sender: str) -> dict:
    """
    Classify an email with Claude.

    Returns a dict with keys:
      is_work_order, is_real_estate, is_skip, property_address,
      sender_name, urgency, treatment_type, summary

    Returns {} on failure — caller should fall back to keyword logic.
    """
    client = _get_client()
    if not client:
        return {}

    prompt = f"""Analyse this email for an Australian pest control business (Zap It Pest & Termite Control, Melbourne).
Return ONLY valid JSON with these exact fields:
- "is_work_order": bool — is this a pest control service request or work order?
- "is_real_estate": bool — is the sender a real estate agent or property manager?
- "is_skip": bool — is this marketing, spam, newsletter, or auto-notification?
- "property_address": string or null — service address mentioned in the email
- "sender_name": string or null — sender's first name
- "urgency": "low" | "medium" | "high"
- "treatment_type": string or null — pest type e.g. "cockroach", "ant", "rodent", "wasp", "bed bug"
- "summary": string — one sentence plain-text summary

From: {sender}
Subject: {subject}
Body: {body[:3000]}"""

    try:
        import anthropic
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(msg.content[0].text)
    except Exception as exc:
        logger.warning("AI email classification failed: %s", exc)
        return {}


def generate_work_order_response(
    sender_name: str,
    property_address: str,
    company_name: str = "",
    treatment_type: str = "",
) -> str:
    """
    Generate a personalised work order acknowledgement email body (plain HTML paragraphs).

    Does NOT include greeting, sign-off, or subject line.
    Returns "" on failure — caller should use the hardcoded template.
    """
    client = _get_client()
    if not client:
        return ""

    context_lines = [f"Sender: {sender_name or 'the property manager'}"]
    if property_address:
        context_lines.append(f"Property address: {property_address}")
    if company_name:
        context_lines.append(f"Property management company: {company_name}")
    if treatment_type:
        context_lines.append(f"Treatment type requested: {treatment_type}")

    prompt = f"""Write a brief, warm email body acknowledging receipt of a pest control work order.
2-3 sentences. Australian English. Professional but human.
Do NOT include "Hi [name]", a sign-off, or a subject line — just the paragraph(s).
Do NOT use placeholder brackets like [date] or [time].

{chr(10).join(context_lines)}
Responding as: Tammy, Zap It Pest & Termite Control Melbourne"""

    try:
        import anthropic
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning("AI response generation failed: %s", exc)
        return ""


def summarise_emails(emails: list) -> str:
    """
    Generate a concise plain-text summary of a batch of emails.
    Returns "" on failure.
    """
    client = _get_client()
    if not client or not emails:
        return ""

    lines = [
        f"- From: {e.get('from', '')} | {e.get('subject', '')} | {e.get('snippet', '')[:100]}"
        for e in emails[:40]
    ]

    prompt = f"""Summarise these business emails for the owner of a pest control company in Melbourne.
Group by theme. Flag work orders and urgent items at the top. Australian English. Under 200 words.

{chr(10).join(lines)}"""

    try:
        import anthropic
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning("AI email summarisation failed: %s", exc)
        return ""


def generate_report_notes(
    job_description: str,
    treatment: str,
    location: str,
) -> str:
    """
    Generate professional pest control inspection notes for a commercial report.
    Returns "" on failure.
    """
    client = _get_client()
    if not client:
        return ""

    prompt = f"""Write 2-3 sentences of professional pest control service notes for a commercial inspection report.
Technical but readable. Australian English. No headings or labels — just the notes paragraph.

Job description: {job_description}
Treatment applied: {treatment}
Location: {location}"""

    try:
        import anthropic
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning("AI report note generation failed: %s", exc)
        return ""
