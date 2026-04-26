"""
Startup health check — run before launching the scheduler.
Tests every configured API key and reports pass/fail.
"""

import os
import sys
import urllib.request
import urllib.error
import json
from dotenv import load_dotenv

load_dotenv()

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"

results = {}


def check(name: str, url: str, headers: dict, expect_status: int = 200) -> bool:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        print(f"  [{FAIL}] {name}: {e}")
        results[name] = False
        return False

    ok = status == expect_status
    tag = PASS if ok else FAIL
    print(f"  [{tag}] {name}: HTTP {status}")
    results[name] = ok
    return ok


print("\n=== Zap It AI Bot — API Health Check ===\n")

# ServiceM8
sm8 = os.getenv("Sm8", "")
if sm8 and "NEEDS" not in sm8:
    check("ServiceM8", "https://api.servicem8.com/api_1.0/staff.json",
          {"x-api-key": sm8})
else:
    print(f"  [{SKIP}] ServiceM8: no key set")

# Square
sq = os.getenv("Square", "")
if sq and "NEEDS" not in sq:
    check("Square", "https://connect.squareup.com/v2/locations",
          {"Square-Version": "2024-03-20", "Authorization": f"Bearer {sq}"})
else:
    print(f"  [{SKIP}] Square: no key set")

# GoHighLevel
ghl = os.getenv("Gohighlevel", "")
if ghl and "NEEDS" not in ghl:
    check("GoHighLevel", "https://rest.gohighlevel.com/v1/contacts/",
          {"Authorization": f"Bearer {ghl}"})
else:
    print(f"  [{SKIP}] GoHighLevel: no key set")

# Formatize
fmt = os.getenv("Formatize", "")
if fmt and "NEEDS" not in fmt:
    check("Formatize", "https://api.formatize.com.au/v1/invoices",
          {"Authorization": f"Bearer {fmt}"})
else:
    print(f"  [{SKIP}] Formatize: no key set")

# GorillaDesk
gd = os.getenv("Gorilladesk", "")
if gd and "NEEDS" not in gd:
    check("GorillaDesk", "https://app.gorilladesk.com/api/v1/customers",
          {"Authorization": f"Bearer {gd}"})
else:
    print(f"  [{SKIP}] GorillaDesk: no key set")

# Gemini
gem = os.getenv("GEMINI_API_KEY", "")
if gem:
    check("Gemini",
          f"https://generativelanguage.googleapis.com/v1beta/models?key={gem}",
          {})
else:
    print(f"  [{SKIP}] Gemini: no key set")

# OpenAI
oai = os.getenv("OPENAI_API_KEY", "")
if oai and "NEEDS" not in oai:
    check("OpenAI", "https://api.openai.com/v1/models",
          {"Authorization": f"Bearer {oai}"})
else:
    print(f"  [{SKIP}] OpenAI: no key set")

# Anthropic
ant = os.getenv("ANTHROPIC_API_KEY", "")
if ant and "NEEDS" not in ant:
    check("Anthropic", "https://api.anthropic.com/v1/models",
          {"x-api-key": ant, "anthropic-version": "2023-06-01"})
else:
    print(f"  [{SKIP}] Anthropic: no key set")

# Summary
passed = sum(1 for v in results.values() if v)
total = len(results)
print(f"\n{'='*40}")
print(f"  {passed}/{total} APIs responding correctly")

critical = {"ServiceM8": results.get("ServiceM8"), "Square": results.get("Square")}
if any(v is False for v in critical.values()):
    print("  WARNING: Critical APIs (SM8/Square) are failing.")
    print("  Note: 403 'Host not in allowlist' means keys are valid but")
    print("  this machine's IP is blocked — will work on your server.\n")
else:
    print("  Core automation APIs ready.\n")
