"""
One-time Google OAuth2 setup.

Run this once on your machine to connect Gmail and Google Sheets:
  python setup_google_auth.py

Prerequisites:
  1. Go to https://console.cloud.google.com
  2. Select or create a project
  3. Enable these APIs:
       - Gmail API
       - Google Sheets API
  4. Go to APIs & Services → Credentials
  5. Click "Create Credentials" → OAuth 2.0 Client ID → Desktop app
  6. Download the JSON file and save it as:
       google_credentials.json   (in this folder)
  7. Run this script — a browser window will open to authorise access
  8. Done — .google_token.json is saved and the bot will use it automatically
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    creds_file = Path("google_credentials.json")
    token_file = Path(".google_token.json")

    if not creds_file.exists():
        print("\n  ERROR: google_credentials.json not found.\n")
        print("  Steps to get it:")
        print("    1. Go to https://console.cloud.google.com")
        print("    2. Create a project (or select existing)")
        print("    3. Enable: Gmail API  +  Google Sheets API")
        print("    4. APIs & Services → Credentials → Create OAuth 2.0 Client ID")
        print("    5. Application type: Desktop app")
        print("    6. Download JSON → rename to google_credentials.json")
        print("    7. Place it in this folder and re-run this script\n")
        sys.exit(1)

    try:
        from utils.google_oauth import get_credentials
        creds = get_credentials()

        if creds and creds.valid:
            print("\n  Google auth successful!")
            print(f"  Token saved to: {token_file}")
            print("\n  Testing Gmail access...")
            _test_gmail(creds)
            print("  Testing Sheets access...")
            _test_sheets(creds)
            print("\n  All good — bot is ready to run.\n")
        else:
            print("\n  Auth failed — credentials not valid.\n")
            sys.exit(1)

    except Exception as exc:
        print(f"\n  Error: {exc}\n")
        sys.exit(1)


def _test_gmail(creds):
    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    print(f"    Gmail connected as: {profile.get('emailAddress')}")


def _test_sheets(creds):
    from googleapiclient.discovery import build
    from config import COMMERCIAL_SHEET_ID
    service = build("sheets", "v4", credentials=creds)
    result = service.spreadsheets().get(spreadsheetId=COMMERCIAL_SHEET_ID).execute()
    print(f"    Sheets connected: '{result.get('properties', {}).get('title', 'OK')}'")


if __name__ == "__main__":
    main()
