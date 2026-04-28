"""
Google OAuth2 token manager for Gmail and Google Sheets.

Handles credential loading, browser-based auth flow, and auto-refresh.
Tokens saved to .google_token.json (gitignored).

Required one-time setup:
  1. Go to https://console.cloud.google.com
  2. Create a project → Enable Gmail API + Google Sheets API
  3. APIs & Services → Credentials → Create OAuth 2.0 Client ID (Desktop app)
  4. Download JSON → save as google_credentials.json in this folder
  5. Run: python setup_google_auth.py
"""

import json
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
]

CREDENTIALS_FILE = Path("google_credentials.json")
TOKEN_FILE = Path(".google_token.json")


def get_credentials() -> Credentials:
    """
    Return valid Google credentials, refreshing or re-running auth as needed.
    Raises FileNotFoundError if google_credentials.json doesn't exist yet.
    """
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        logger.info("Refreshing Google access token")
        creds.refresh(Request())
        _save(creds)
        return creds

    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"{CREDENTIALS_FILE} not found.\n"
            "Download it from Google Cloud Console:\n"
            "  APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON\n"
            "Then run: python setup_google_auth.py"
        )

    logger.info("Running Google OAuth browser flow")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    _save(creds)
    return creds


def _save(creds: Credentials) -> None:
    TOKEN_FILE.write_text(creds.to_json())
    logger.info("Google token saved to %s", TOKEN_FILE)


def is_authenticated() -> bool:
    """Return True if valid credentials exist without prompting."""
    try:
        creds = get_credentials()
        return creds is not None and creds.valid
    except Exception:
        return False
