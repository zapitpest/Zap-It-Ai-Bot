"""
Zap Bot — Local Command Centre
Run: python main.py

A safe local interface to inspect, draft, and control the bot.
Any action that affects a real customer system requires typing:
  APPROVE ACTION
before it runs.
"""

import os
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

BANNER = """
╔══════════════════════════════════════════════════════════╗
║            Zap Bot — Local Command Centre                ║
║        Zap It Pest & Termite Control Melbourne           ║
╚══════════════════════════════════════════════════════════╝
Type a command or question. Type 'help' to see what's available.
Type 'exit' or Ctrl+C to quit.
"""

HELP_TEXT = """
Available commands:
  status          — Check bot and API connection status
  diagnostics     — Run full diagnostics
  draft email     — Draft an email (will NOT send without APPROVE ACTION)
  help            — Show this help
  exit            — Quit

To run a background automation manually (read-only inspection only):
  run email check — Fetch recent emails and summarise (no replies sent)

Safety rules:
  • No emails are sent without APPROVE ACTION
  • No ServiceM8 jobs are modified
  • No bookings are created or changed
  • No invoices are created
  • No SMS sent
  • No automations triggered
  All destructive actions require typing: APPROVE ACTION
"""

APPROVAL_PHRASE = "APPROVE ACTION"


def ai_available() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key) and key.startswith("sk-ant-")


def ask_ai(prompt: str) -> str:
    """Send a prompt to Claude. Returns response text or an error message."""
    if not ai_available():
        return (
            "⚠  AI provider not available.\n"
            "   The ANTHROPIC_API_KEY in your .env is missing or invalid.\n"
            "   Expected format: sk-ant-api03-...\n"
            "   Get a valid key: https://console.anthropic.com/settings/keys\n"
            "   Then run: python diagnostics.py"
        )
    try:
        import anthropic
        key = os.getenv("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=(
                "You are the AI assistant for Zap It Pest & Termite Control Melbourne. "
                "You help the owner inspect business data, draft communications, and suggest improvements. "
                "You do NOT send emails, modify jobs, create bookings, or take any real action "
                "unless the user explicitly types 'APPROVE ACTION'. "
                "Always be concise, professional, and use Australian English."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        err = str(exc)
        if "invalid_api_key" in err or "authentication" in err.lower():
            return "⚠  AI rejected the request: invalid API key. Run python diagnostics.py"
        elif "monthly" in err.lower() or "usage" in err.lower() or "quota" in err.lower():
            return "⚠  AI usage limit reached. Check billing: https://console.anthropic.com/settings/billing"
        elif "credit" in err.lower():
            return "⚠  No AI credits. Add credits: https://console.anthropic.com/settings/billing"
        return f"⚠  AI error: {err}\n   Run python diagnostics.py for details."


def require_approval(action_description: str) -> bool:
    """Ask user to explicitly approve a real-world action. Returns True if approved."""
    print(f"\n⚠  This action will: {action_description}")
    print(f"   To confirm, type exactly: {APPROVAL_PHRASE}")
    print(f"   To cancel, press Enter or type anything else.")
    response = input("   > ").strip()
    if response == APPROVAL_PHRASE:
        print("   ✓ Action approved.")
        return True
    print("   ✗ Action cancelled.")
    return False


def cmd_status():
    """Show current bot and API status."""
    print("\n── Bot Status ─────────────────────────────────────")
    print(f"  Time (UTC)  : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  AI provider : Anthropic Claude")
    print(f"  AI model    : claude-haiku-4-5-20251001")
    print(f"  AI ready    : {'✓ Yes' if ai_available() else '✗ No — invalid ANTHROPIC_API_KEY'}")

    keys = {
        "ServiceM8":  os.getenv("Sm8", ""),
        "GoHighLevel": os.getenv("Gohighlevel", ""),
        "Gmail SMTP": os.getenv("GMAIL_APP_PASSWORD", ""),
        "Meta Ads":   os.getenv("META_ADS_TOKEN", ""),
        "Square":     os.getenv("Square", ""),
    }
    print("\n  Configured APIs:")
    for name, val in keys.items():
        tag = "✓" if val else "✗ MISSING"
        print(f"    {tag}  {name}")

    if not ai_available():
        print("\n  ⚠  BLOCKER: Fix ANTHROPIC_API_KEY before AI features will work.")
        print("     Get a key: https://console.anthropic.com/settings/keys")
    print()


def cmd_diagnostics():
    """Run diagnostics.py as a subprocess."""
    import subprocess
    result = subprocess.run([sys.executable, "diagnostics.py"], capture_output=False)


def cmd_draft_email():
    """Interactive email drafter — never sends without APPROVE ACTION."""
    print("\n── Draft Email ────────────────────────────────────")
    print("  This will draft an email. It will NOT be sent until you APPROVE ACTION.\n")
    to = input("  To (email address): ").strip()
    subject = input("  Subject: ").strip()
    context = input("  What should the email say? (brief notes): ").strip()

    if not to or not subject or not context:
        print("  Cancelled — missing fields.")
        return

    print("\n  Drafting with AI...")
    draft = ask_ai(
        f"Draft a professional email for Zap It Pest & Termite Control Melbourne.\n"
        f"To: {to}\nSubject: {subject}\nContext: {context}\n"
        f"Use Australian English. Sign off as Tammy. Keep it concise."
    )

    print(f"\n── Draft ──────────────────────────────────────────")
    print(f"  To: {to}")
    print(f"  Subject: {subject}")
    print(f"\n{draft}\n")
    print("──────────────────────────────────────────────────")

    if require_approval(f"send this email to {to}"):
        try:
            from utils.gmail_client import send_email
            send_email(to, subject, draft)
            print(f"  ✓ Email sent to {to}")
        except Exception as exc:
            print(f"  ✗ Send failed: {exc}")
    print()


def cmd_run_email_check():
    """Fetch and summarise recent emails — read only, no replies."""
    print("\n── Email Check (read-only) ────────────────────────")
    print("  Fetching recent emails from Gmail... (no replies will be sent)\n")
    try:
        from utils.gmail_client import emails_since
        emails = emails_since(hours=24)
        if not emails:
            print("  No emails found in the last 24 hours.")
            return
        print(f"  Found {len(emails)} email(s). Summarising...\n")
        summary = ask_ai(
            "Summarise these emails for the owner of Zap It Pest Control Melbourne. "
            "Flag any urgent work orders at the top. Australian English. Under 150 words.\n\n"
            + "\n".join(
                f"- From: {e.get('from','')} | {e.get('subject','')} | {e.get('snippet','')[:100]}"
                for e in emails[:20]
            )
        )
        print(summary)
    except Exception as exc:
        print(f"  ✗ Email check failed: {exc}")
    print()


def handle_freeform(text: str):
    """Send freeform input to AI as a general question."""
    print("\n  Thinking...")
    response = ask_ai(text)
    print(f"\n{response}\n")


def main():
    print(BANNER)
    if not ai_available():
        print("⚠  WARNING: AI provider not ready.")
        print("   ANTHROPIC_API_KEY is missing or invalid (current value starts with 'EAAAl5...').")
        print("   Get a valid key: https://console.anthropic.com/settings/keys")
        print("   Run python diagnostics.py for full details.\n")

    while True:
        try:
            text = input("zap-bot> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not text:
            continue

        lower = text.lower()

        if lower in ("exit", "quit", "q"):
            print("Goodbye.")
            break
        elif lower == "help":
            print(HELP_TEXT)
        elif lower == "status":
            cmd_status()
        elif lower in ("diagnostics", "diag"):
            cmd_diagnostics()
        elif lower.startswith("draft email"):
            cmd_draft_email()
        elif lower.startswith("run email check"):
            cmd_run_email_check()
        else:
            handle_freeform(text)


if __name__ == "__main__":
    main()
