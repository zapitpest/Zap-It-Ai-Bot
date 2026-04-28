"""
Zap Bot — Diagnostics
Run: python diagnostics.py

Checks config, env vars, and makes a live test call to the AI provider.
Never prints full secrets.
"""

import os
import sys
import platform

# ── Load .env ────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    dotenv_ok = True
except ImportError:
    dotenv_ok = False

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
WARN = "\033[93m WARN\033[0m"
INFO = "\033[94m INFO\033[0m"


def mask(val: str) -> str:
    if not val:
        return "(not set)"
    if len(val) <= 10:
        return "****"
    return val[:6] + "****" + val[-4:]


def section(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


# ── 1. Environment ────────────────────────────────────────────────────────────
section("1. Environment")
print(f"  Project root : {os.path.dirname(os.path.abspath(__file__))}")
print(f"  Python       : {platform.python_version()} ({sys.executable})")
print(f"  Platform     : {platform.system()} {platform.release()}")
print(f"  .env loaded  : {'Yes' if dotenv_ok else FAIL + ' python-dotenv not installed'}")

# ── 2. Required env vars ──────────────────────────────────────────────────────
section("2. Environment Variables")

REQUIRED = {
    "ANTHROPIC_API_KEY": "Anthropic Claude (AI)",
    "Sm8": "ServiceM8",
    "Gohighlevel": "GoHighLevel CRM",
    "META_ADS_TOKEN": "Meta Ads",
    "META_AD_ACCOUNT_ID": "Meta Ad Account",
    "GMAIL_APP_PASSWORD": "Gmail SMTP",
    "COMMERCIAL_SHEET_ID": "Google Sheet",
}
OPTIONAL = {
    "OPENAI_API_KEY": "OpenAI (optional fallback)",
    "MANUS_API_KEY": "Manus AI (optional)",
    "Square": "Square bookings (optional)",
}

all_ok = True
for key, label in REQUIRED.items():
    val = os.getenv(key, "")
    if val:
        # Warn if Anthropic key format looks wrong
        if key == "ANTHROPIC_API_KEY" and not val.startswith("sk-ant-"):
            print(f" [{WARN}] {key} ({label}): {mask(val)}")
            print(f"         ⚠ This does not look like a valid Anthropic key.")
            print(f"           Real keys start with 'sk-ant-'. Get one at:")
            print(f"           https://console.anthropic.com/settings/keys")
            all_ok = False
        else:
            print(f" [{PASS}] {key} ({label}): {mask(val)}")
    else:
        print(f" [{FAIL}] {key} ({label}): MISSING")
        all_ok = False

for key, label in OPTIONAL.items():
    val = os.getenv(key, "")
    tag = INFO if val else WARN
    print(f" [{tag}] {key} ({label}): {mask(val)}")

# ── 3. AI provider test ───────────────────────────────────────────────────────
section("3. AI Provider Test")

anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
ai_passed = False

if not anthropic_key:
    print(f" [{FAIL}] ANTHROPIC_API_KEY is not set — skipping live test")
elif not anthropic_key.startswith("sk-ant-"):
    print(f" [{FAIL}] ANTHROPIC_API_KEY format is invalid (starts with '{anthropic_key[:8]}...')")
    print(f"         Expected format: sk-ant-api03-...")
    print(f"         Get a valid key: https://console.anthropic.com/settings/keys")
else:
    print(f"  Testing Anthropic API with key {mask(anthropic_key)} ...")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": "Reply with: OK"}],
        )
        response = msg.content[0].text.strip()
        print(f" [{PASS}] Anthropic API responded: '{response}'")
        ai_passed = True
    except Exception as exc:
        err = str(exc)
        print(f" [{FAIL}] Anthropic API call failed: {err}")
        if "invalid_api_key" in err or "authentication" in err.lower():
            print(f"         → The API key is invalid or expired.")
            print(f"           Get a new key: https://console.anthropic.com/settings/keys")
        elif "monthly" in err.lower() or "usage" in err.lower() or "quota" in err.lower():
            print(f"         → Usage limit hit. Check billing:")
            print(f"           https://console.anthropic.com/settings/billing")
        elif "credit" in err.lower():
            print(f"         → No credits. Add credits:")
            print(f"           https://console.anthropic.com/settings/billing")

# ── 4. Summary ────────────────────────────────────────────────────────────────
section("4. Summary")
if ai_passed and all_ok:
    print(f" [{PASS}] Everything looks good. Run the bot with:")
    print(f"          python scheduler.py")
    print(f"          python utils/api_server.py  (web dashboard on port 5000)")
else:
    print(f" [{FAIL}] Issues found. Fix the items above, then re-run:")
    print(f"          python diagnostics.py")
    if not anthropic_key or not anthropic_key.startswith("sk-ant-"):
        print(f"\n  MOST LIKELY CAUSE: Invalid Anthropic API key.")
        print(f"  Fix: Get a valid key at https://console.anthropic.com/settings/keys")
        print(f"  Then update ANTHROPIC_API_KEY in your .env file")

print()
