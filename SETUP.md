# Zap It AI Bot — Setup Guide

## Quick Start (3 steps)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate Gmail App Password
Gmail SMTP is built-in — no OAuth setup needed.

**One-time setup:**
1. Go to https://myaccount.google.com/apppasswords
2. Select: **Mail** → **Windows Computer** (or your device)
3. Google generates a 16-character password
4. Copy it and add to `.env`:
   ```
   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

That's it — the bot can now send and read emails.

### 3. Add your API keys to `.env`

Copy these from your cloud setup:
```bash
Sm8=your-servicem8-key
ANTHROPIC_API_KEY=your-claude-key
OPENAI_API_KEY=your-openai-key
Gohighlevel=your-ghl-key
MANUS_API_KEY=your-manus-key
META_ADS_TOKEN=your-meta-token
META_AD_ACCOUNT_ID=act_XXXXXXXXX
COMMERCIAL_SHEET_ID=1dDZdZ01d5MjdwYkfwxHgNvFisa1wQL_ReWZYR6RJZ7o
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 4. (Optional) Learn your preferences
```bash
python -m utils.manus_client --learn
```
Manus teaches the bot your email tone and priorities.

### 5. Start the bot
```bash
python scheduler.py
```

Done. The bot now runs 7 automations automatically:
- **7:00 AM** — Morning email summary
- **5:00 PM** — Afternoon email summary  
- **Every hour** — Auto-respond to real estate work orders
- **7 AM & 7 PM** — Follow-up on unresponded orders
- **Mon/Wed/Fri 8 PM** — Sync ServiceM8 → Google Sheet
- **9:00 AM** — Sync ServiceM8 → GoHighLevel CRM
- **Every 30 min** — Pull Meta Ads leads → create jobs

---

## Troubleshooting

### Gmail not working?
```bash
python -c "from utils.gmail_client import send_email; send_email('your@email.com', 'Test', 'Hello')"
```
If it fails: check your `GMAIL_APP_PASSWORD` is correct (no spaces).

### Check which APIs are connected
```bash
python health_check.py
```

### Re-enable flyers (disabled by default)
Edit `scheduler.py` and uncomment the flyer lines.

---

## Architecture

The bot is 7 loosely-coupled automations that run on a schedule:

| Automation | Interval | What it does |
|---|---|---|
| morning_email_summary | 7 AM | Scans Gmail, sends daily summary |
| afternoon_email_summary | 5 PM | Same, 10-hour window |
| email_auto_responder | Hourly | Responds to real estate work orders (AI-powered) |
| unresponded_email_followup | 7 AM, 7 PM | Alerts on ignored work orders |
| google_sheet_sm8_sync | Mon/Wed/Fri 8 PM | Updates commercial client sheet |
| crm_sync | 9 AM | Syncs SM8 companies → GoHighLevel |
| meta_lead_sync | Every 30 min | Pulls Facebook/Instagram leads → jobs + contacts |

Each is in `automations/` and can be run standalone or disabled.

---

## Files

- `scheduler.py` — main orchestrator, runs all automations
- `config.py` — loads .env, defines API keys and business settings
- `utils/` — reusable clients (Gmail, ServiceM8, Sheets, GHL, Meta, etc.)
- `automations/` — individual scheduled tasks
- `health_check.py` — diagnoses connection issues

---

## Customization

**Disable an automation:** Comment it out in `scheduler.py`.

**Change a schedule:** Edit the `schedule.every()...` line in `scheduler.py`.

**Adjust email tone:** Run `python -m utils.manus_client --learn` again.

**Change which real estate companies get auto-responses:** Edit `email_classifier.py` REAL_ESTATE_KEYWORDS.

---

## Support

If something breaks:
1. Run `python health_check.py` to see which APIs are down
2. Check the logs (look for errors in console)
3. Test individual modules: `python -m automations.<name>`

---

Happy automating! 🚀
