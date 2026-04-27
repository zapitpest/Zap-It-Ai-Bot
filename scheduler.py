"""
Zap It AI Bot — Main Scheduler

Automation schedule:
  Morning Email Summary      7:00 AM daily        (cron: 0 7 * * *)
  Afternoon Email Summary    5:00 PM daily         (cron: 0 17 * * *)
  Email Auto-Responder       Every hour            (interval: 3600s)
  Unresponded Email Follow-Up 7:00 AM & 7:00 PM   (cron: 0 7,19 * * *)
  Google Sheet SM8 Sync      8:00 PM Mon/Wed/Fri   (cron: 0 20 * * 1,3,5)
  Treatment Flyer Send       Every hour (after SM8) (interval: 3600s, offset 30m)
  CRM Sync (SM8 → GHL)       9:00 AM daily        (cron: 0 9 * * *)

All times are Melbourne local time (Australia/Melbourne).
"""

import logging
import time
import traceback
from datetime import datetime

import pytz
import schedule

from automations.morning_email_summary import run as morning_summary
from automations.afternoon_email_summary import run as afternoon_summary
from automations.google_sheet_sm8_sync import run as sheet_sm8_sync
from automations.email_auto_responder import run as auto_responder
from automations.unresponded_email_followup import run as followup_check
from automations.crm_sync import run as crm_sync
from send_flyers import run as send_flyers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scheduler")

MELBOURNE_TZ = pytz.timezone("Australia/Melbourne")


def _safe_run(name: str, fn, *args, **kwargs) -> None:
    """Wrap an automation in try/except so one failure doesn't crash the scheduler."""
    logger.info(">>> Starting: %s", name)
    try:
        fn(*args, **kwargs)
        logger.info("<<< Completed: %s", name)
    except Exception:
        logger.error("!!! Error in %s:\n%s", name, traceback.format_exc())


def _melbourne_time() -> str:
    return datetime.now(MELBOURNE_TZ).strftime("%H:%M")


# --- Schedule definitions ---

schedule.every().day.at("07:00").do(
    lambda: _safe_run("Morning Email Summary", morning_summary)
)

schedule.every().day.at("17:00").do(
    lambda: _safe_run("Afternoon Email Summary", afternoon_summary)
)

schedule.every().day.at("07:00").do(
    lambda: _safe_run("Unresponded Email Follow-Up (AM)", followup_check)
)

schedule.every().day.at("19:00").do(
    lambda: _safe_run("Unresponded Email Follow-Up (PM)", followup_check)
)

# Mon=0, Wed=2, Fri=4 in schedule library
schedule.every().monday.at("20:00").do(
    lambda: _safe_run("Google Sheet SM8 Sync (Mon)", sheet_sm8_sync)
)
schedule.every().wednesday.at("20:00").do(
    lambda: _safe_run("Google Sheet SM8 Sync (Wed)", sheet_sm8_sync)
)
schedule.every().friday.at("20:00").do(
    lambda: _safe_run("Google Sheet SM8 Sync (Fri)", sheet_sm8_sync)
)

schedule.every(1).hours.do(
    lambda: _safe_run("Email Auto-Responder", auto_responder)
)

schedule.every(1).hours.do(
    lambda: _safe_run("Treatment Flyer Send", send_flyers, hours=2)
)

schedule.every().day.at("09:00").do(
    lambda: _safe_run("CRM Sync (SM8 → GHL)", crm_sync)
)


def main() -> None:
    logger.info("Zap It AI Bot scheduler starting — Melbourne time: %s",
                _melbourne_time())
    logger.info("Pending jobs: %d", len(schedule.jobs))

    # Run auto-responder and flyer check immediately on startup
    _safe_run("Email Auto-Responder (startup)", auto_responder)
    _safe_run("Treatment Flyer Send (startup)", send_flyers, hours=24)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
