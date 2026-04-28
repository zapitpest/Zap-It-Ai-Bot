import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
SM8_API_KEY = os.environ["Sm8"]
SQUARE_API_KEY = os.environ["Square"]
GORILLADESK_API_KEY = os.environ.get("Gorilladesk", "")
QUICKBOOKS_API_KEY = os.environ.get("Quickbooks", "")
GOHIGHLEVEL_API_KEY = os.environ.get("Gohighlevel", "")
# Formatize is legacy invoicing — not used in active automations
FORMATIZE_API_KEY = os.environ.get("Formatize", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
MANUS_API_KEY = os.environ.get("MANUS_API_KEY", "")
MANUS_API_BASE = os.environ.get("MANUS_API_BASE", "https://api.manus.ai/v1")
MANUS_AGENT_ID = os.environ.get("MANUS_AGENT_ID", "")
META_ADS_TOKEN = os.environ.get("META_ADS_TOKEN", "")
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "")

# --- ServiceM8 ---
SM8_BASE_URL = "https://api.servicem8.com/api_1.0"
SM8_HEADERS = {
    "x-api-key": SM8_API_KEY,
    "Content-Type": "application/json",
}

# --- Square ---
SQUARE_BASE_URL = "https://connect.squareup.com/v2"
SQUARE_HEADERS = {
    "Square-Version": "2024-03-20",
    "Authorization": f"Bearer {SQUARE_API_KEY}",
    "Content-Type": "application/json",
}

# --- Business Identity ---
BUSINESS_NAME = "Zap It Pest & Termite Control Melbourne"
BUSINESS_PHONE = "03 9126 0555"
BUSINESS_EMAIL = "info@zapitpestmelbourne.com.au"
SIGNATURE_NAME = "Tammy"

# --- Bank Details ---
BANK_ACCOUNT_NAME = "Prime Solutions Group"
BANK_BSB = "033143"
BANK_ACCOUNT_NUMBER = "649414"

# --- CDN Assets ---
LOGO_GREEN_BG = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663545416636/lSEcoAlPePfSIILp.png"
LOGO_WHITE_BG = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663545416636/EZGAxpJhigjwcMUe.png"

# --- Flyer URLs ---
FLYER_GENERAL = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663545416636/jRqQsEMQLQmvbGet.html"
FLYER_COCKROACH_FAQ = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663545416636/hwVTcTAtPVthjXcJ.html"

FLYER_URL_MAP = {
    "general": FLYER_GENERAL,
    "cockroach": FLYER_COCKROACH_FAQ,
    "cockroaches": FLYER_COCKROACH_FAQ,
}

# Treatments that trigger flyer sends for commercial/real estate clients
COMMERCIAL_FLYER_TREATMENTS = {
    "wasp", "wasps", "moth", "moths", "rodent", "rodents", "rat", "rats",
    "mouse", "mice", "bed bug", "bed bugs", "bedbug", "bedbugs",
    "possum", "possums", "ant", "ants",
}

# --- Google Sheets ---
COMMERCIAL_SHEET_ID = os.environ.get(
    "COMMERCIAL_SHEET_ID",
    "1dDZdZ01d5MjdwYkfwxHgNvFisa1wQL_ReWZYR6RJZ7o",
)
COMMERCIAL_SHEET_TAB = "Commercial Clients"

# --- Report Templates ---
COMMERCIAL_REPORT_URL = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663545416636/ehyGnRRWfOFqyVXM.html"
RESIDENTIAL_REPORT_URL = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663545416636/rExohyhXrojQdATI.html"

# --- Debt Collection ---
VIC_COLLECT_PORTAL = "https://www.viccollect.com.au"
VIC_COLLECT_USERNAME = "ZIP"
VIC_COLLECT_CONTACT = "Mark White"
VIC_COLLECT_PHONE = "03 5792 2708"

# --- Tracking Files ---
FLYERS_SENT_FILE = "flyers_sent.json"

# --- Timezone ---
TIMEZONE = "Australia/Melbourne"
