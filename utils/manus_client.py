"""
Manus AI agent client.

Manus exposes an OpenAI-compatible API at api.manus.ai/v1.
This client uses it to:
  - Send tasks/instructions to Manus and receive AI responses
  - Query Manus for bot behaviour preferences and business rules
  - Run a one-time "learning" conversation to extract what the user
    wants from this bot, then persist results to manus_prefs.json

NOTE: Manus restricts API calls by IP. If you see "Host not in allowlist",
add this server's IP to your Manus account allowlist, or run from your
local machine.

Auth: Bearer token (MANUS_API_KEY from .env)
Base: MANUS_API_BASE (default: https://api.manus.ai/v1)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import MANUS_API_KEY, MANUS_API_BASE, MANUS_AGENT_ID

logger = logging.getLogger(__name__)

PREFS_FILE = Path("manus_prefs.json")

SYSTEM_CONTEXT = """You are helping configure an AI automation bot called Zap It AI Bot.
This bot runs automations for Zap It Pest & Termite Control Melbourne — an Australian pest control business.

Current automations:
- Morning and afternoon email summaries (7 AM, 5 PM)
- Email auto-responder for real estate work orders
- Unresponded email follow-up alerts (7 AM, 7 PM)
- Treatment aftercare flyer emails (hourly)
- Google Sheet ↔ ServiceM8 sync (Mon/Wed/Fri 8 PM)
- ServiceM8 → GoHighLevel CRM sync (daily 9 AM)

The bot connects to: ServiceM8, Square, GoHighLevel, GorillaDesk,
QuickBooks, Gmail, Google Sheets, Anthropic Claude, OpenAI.

Your role: answer questions about what the business owner wants this bot
to do, help refine automation logic, and suggest improvements."""


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {MANUS_API_KEY}",
        "Content-Type": "application/json",
    }


def _chat(messages: list, model: str = "gpt-4o", max_tokens: int = 1024) -> str:
    """
    Send a chat request to Manus's OpenAI-compatible API.
    Returns the assistant reply text, or raises on failure.
    """
    if not MANUS_API_KEY:
        raise RuntimeError("MANUS_API_KEY not set in .env")

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if MANUS_AGENT_ID:
        payload["agent_id"] = MANUS_AGENT_ID

    r = requests.post(
        f"{MANUS_API_BASE}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def ask(question: str, context: str = "") -> str:
    """
    Ask Manus a single question about the bot's desired behaviour.
    Returns Manus's answer as plain text.
    """
    messages = [
        {"role": "system", "content": SYSTEM_CONTEXT},
    ]
    if context:
        messages.append({"role": "user", "content": f"Context: {context}"})
    messages.append({"role": "user", "content": question})

    logger.info("Asking Manus: %s", question[:80])
    reply = _chat(messages)
    logger.info("Manus replied (%d chars)", len(reply))
    return reply


def learn_preferences() -> dict:
    """
    Run a structured conversation with Manus to learn what the business
    owner wants from this bot. Saves results to manus_prefs.json.

    Returns the preferences dict.
    """
    logger.info("Starting Manus preference learning session")

    questions = [
        (
            "email_response_style",
            "How should the bot write email responses to real estate property managers? "
            "Describe the tone, length, and any specific phrases to use or avoid. "
            "Consider the business is Australian and the contact is Tammy.",
        ),
        (
            "work_order_priorities",
            "Which types of pest control work orders should the bot treat as urgent "
            "and flag immediately? Which can wait for the standard response window?",
        ),
        (
            "commercial_client_rules",
            "Are there any commercial clients the bot should treat differently? "
            "For example: always prioritise, never auto-respond, invoice only, skip entirely.",
        ),
        (
            "flyer_preferences",
            "Should aftercare flyers be sent to all clients after every job, or only "
            "specific treatment types? Are there clients who should never receive flyers?",
        ),
        (
            "crm_sync_rules",
            "When syncing ServiceM8 clients to GoHighLevel CRM, which clients should "
            "be tagged as high-value? What pipeline stage should new clients start in?",
        ),
        (
            "new_automations",
            "What additional automations would be most useful for the pest control business? "
            "Think about: invoicing, reminders, follow-ups, reporting, or client communication.",
        ),
    ]

    prefs = {
        "learned_at": datetime.now(timezone.utc).isoformat(),
        "source": "manus",
    }

    conversation = [{"role": "system", "content": SYSTEM_CONTEXT}]

    for key, question in questions:
        conversation.append({"role": "user", "content": question})
        try:
            answer = _chat(conversation, max_tokens=512)
            prefs[key] = answer
            conversation.append({"role": "assistant", "content": answer})
            logger.info("Learned preference: %s", key)
        except Exception as exc:
            logger.error("Failed to learn '%s': %s", key, exc)
            prefs[key] = None

    PREFS_FILE.write_text(json.dumps(prefs, indent=2))
    logger.info("Preferences saved to %s", PREFS_FILE)
    return prefs


def load_preferences() -> dict:
    """Load previously learned preferences from manus_prefs.json."""
    if PREFS_FILE.exists():
        return json.loads(PREFS_FILE.read_text())
    return {}


def get_preference(key: str, fallback: str = "") -> str:
    """Get a single preference value, returning fallback if not found."""
    return load_preferences().get(key, fallback)


def suggest_email_response(
    sender_name: str,
    property_address: str,
    company_name: str = "",
    treatment_type: str = "",
) -> str:
    """
    Ask Manus to generate a work order response using learned style preferences.
    Falls back to empty string on failure.
    """
    style = get_preference("email_response_style", "")
    style_note = f"\n\nStyle guidance from business owner:\n{style}" if style else ""

    messages = [
        {"role": "system", "content": SYSTEM_CONTEXT + style_note},
        {
            "role": "user",
            "content": (
                f"Write a brief email body (2-3 sentences) acknowledging a pest control work order.\n"
                f"Sender: {sender_name or 'the property manager'}\n"
                f"Property: {property_address or 'the property'}\n"
                f"Company: {company_name or ''}\n"
                f"Treatment: {treatment_type or 'general pest control'}\n\n"
                f"Do NOT include greeting, sign-off, or subject line. Australian English."
            ),
        },
    ]

    try:
        return _chat(messages, max_tokens=200)
    except Exception as exc:
        logger.warning("Manus email suggestion failed: %s", exc)
        return ""


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Manus AI client")
    parser.add_argument("--learn", action="store_true",
                        help="Run preference learning session and save to manus_prefs.json")
    parser.add_argument("--ask", type=str, metavar="QUESTION",
                        help="Ask Manus a single question")
    parser.add_argument("--show-prefs", action="store_true",
                        help="Print saved preferences")
    args = parser.parse_args()

    if args.learn:
        prefs = learn_preferences()
        print(json.dumps(prefs, indent=2))

    elif args.ask:
        print(ask(args.ask))

    elif args.show_prefs:
        prefs = load_preferences()
        if prefs:
            print(json.dumps(prefs, indent=2))
        else:
            print("No preferences saved yet. Run: python -m utils.manus_client --learn")

    else:
        parser.print_help()
