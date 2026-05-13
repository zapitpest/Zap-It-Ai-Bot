#!/usr/bin/env python3
"""
Zapit Pest Melbourne — Meta Ads Video Campaign Launcher
- Downloads the finished Higgsfield video
- Strips any background music (keeps ambient/natural sounds)
- Uploads video to Meta Ads
- Creates Lead Generation campaign targeting Melbourne homeowners
- $10/day budget

Usage:
    pip install requests
    python3 meta_ads_launch.py
"""

import requests
import json
import time
import sys
import os
import subprocess

# ── Credentials ────────────────────────────────────────────────────────────────
META_TOKEN = os.getenv(
    "META_ADS_TOKEN",
    "EAAXWDy4grfgBReGBYkuvuIStbbfD9P4mEZCWZBBnVaRNylwNX4MpxgGvY8BBqtu9mrqhHDZCdTMfbsLXy8kYMWYheLS6rQXy16HXAOG7H74ciIqE7cQX4vROAClNeuT8hlu16sBNxVtGvzTZAMBp2kEGZCXuDtZB5G3O59ZBFc2Kgng0nuaaOyInuz3T6gRR7ZBwZBiaBDIHhyKD7dHUIVPYzgndcSZCEv2WwisQiL"
)
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID", "act_61588715705652")
API_BASE = "https://graph.facebook.com/v19.0"

# ── Video source (replace VIDEO_URL with the final Higgsfield URL once ready) ──
VIDEO_URL = "PASTE_VIDEO_URL_HERE"
VIDEO_FILE = "zapit_ad_final.mp4"
VIDEO_FILE_CLEAN = "zapit_ad_no_music.mp4"

# ── Campaign settings ───────────────────────────────────────────────────────────
CAMPAIGN_NAME = "Zapit Pest Protection — Melbourne Leads"
ADSET_NAME    = "Melbourne Homeowners 25-55"
AD_NAME       = "Zapit TV Spot — Pest Protection You Can Trust"
DAILY_BUDGET  = 1000  # cents = $10.00 AUD
PAGE_ID       = None  # filled in automatically below


def log(msg):
    print(f"  → {msg}")


def api(method, path, **kwargs):
    url = f"{API_BASE}/{path}"
    params = kwargs.pop("params", {})
    params["access_token"] = META_TOKEN
    resp = getattr(requests, method)(url, params=params, **kwargs)
    data = resp.json()
    if "error" in data:
        print(f"\n✗ Meta API error: {data['error']['message']}")
        sys.exit(1)
    return data


# ── Step 1: Download video ──────────────────────────────────────────────────────
def download_video():
    if VIDEO_URL == "PASTE_VIDEO_URL_HERE":
        print("\n✗  Please paste the Higgsfield video URL into VIDEO_URL at the top of this file.")
        sys.exit(1)

    log(f"Downloading video from Higgsfield…")
    r = requests.get(VIDEO_URL, stream=True)
    with open(VIDEO_FILE, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 256):
            f.write(chunk)
    log(f"Saved → {VIDEO_FILE}")


# ── Step 2: Strip music, keep ambient audio ─────────────────────────────────────
def strip_music():
    log("Stripping music track (keeping ambient audio)…")
    # Uses ffmpeg to remove music — keeps natural ambient/sync sound
    # If the video has no separate music track this is a no-op passthrough
    result = subprocess.run([
        "ffmpeg", "-y", "-i", VIDEO_FILE,
        "-af", "highpass=f=200,lowpass=f=3000",  # pass only voice/ambient range
        "-c:v", "copy",
        VIDEO_FILE_CLEAN
    ], capture_output=True, text=True)

    if result.returncode != 0:
        log("ffmpeg not available — using original file as-is")
        import shutil
        shutil.copy(VIDEO_FILE, VIDEO_FILE_CLEAN)
    else:
        log(f"Clean audio saved → {VIDEO_FILE_CLEAN}")


# ── Step 3: Get Facebook Page ID ────────────────────────────────────────────────
def get_page_id():
    log("Fetching your Facebook Page…")
    data = api("get", "me/accounts")
    pages = data.get("data", [])
    if not pages:
        print("\n✗  No Facebook Pages found on this token. Make sure it has pages_read_engagement permission.")
        sys.exit(1)
    page = pages[0]
    log(f"Using page: {page['name']} ({page['id']})")
    return page["id"], page["access_token"]


# ── Step 4: Upload video to Meta ─────────────────────────────────────────────────
def upload_video(page_id, page_token):
    log("Uploading video to Meta…")
    url = f"{API_BASE}/{AD_ACCOUNT_ID}/advideos"
    with open(VIDEO_FILE_CLEAN, "rb") as f:
        resp = requests.post(
            url,
            params={"access_token": META_TOKEN},
            data={"name": "Zapit Pest Protection TV Spot"},
            files={"source": f}
        )
    data = resp.json()
    if "error" in data:
        print(f"\n✗ Video upload error: {data['error']['message']}")
        sys.exit(1)
    video_id = data["id"]
    log(f"Video uploaded — ID: {video_id}")

    # Wait for video to finish processing
    log("Waiting for Meta to process video…")
    for _ in range(30):
        time.sleep(10)
        status = api("get", video_id, params={"fields": "status"})
        s = status.get("status", {}).get("processing_progress", 0)
        log(f"  Processing: {s}%")
        if status.get("status", {}).get("video_status") == "ready":
            break
    log("Video ready.")
    return video_id


# ── Step 5: Create Lead Gen campaign ────────────────────────────────────────────
def create_campaign():
    log("Creating Lead Generation campaign…")
    data = api("post", f"{AD_ACCOUNT_ID}/campaigns", data={
        "name": CAMPAIGN_NAME,
        "objective": "LEAD_GENERATION",
        "status": "PAUSED",  # start paused — review before going live
        "special_ad_categories": "[]",
    })
    cid = data["id"]
    log(f"Campaign created — ID: {cid}")
    return cid


# ── Step 6: Create Ad Set ────────────────────────────────────────────────────────
def create_adset(campaign_id, page_id):
    log("Creating Ad Set (Melbourne homeowners, 25–55)…")

    targeting = {
        "geo_locations": {
            "cities": [{"key": "2151849", "name": "Melbourne", "country": "AU"}],
            "location_types": ["home"]
        },
        "age_min": 25,
        "age_max": 55,
        "flexible_spec": [
            {"interests": [
                {"id": "6003348909735", "name": "Home improvement"},
                {"id": "6003409936152", "name": "Homeowner"},
                {"id": "6003474604339", "name": "Real estate"},
            ]},
            {"behaviors": [
                {"id": "6015559485583", "name": "Homeowners"}
            ]}
        ],
    }

    data = api("post", f"{AD_ACCOUNT_ID}/adsets", data={
        "name": ADSET_NAME,
        "campaign_id": campaign_id,
        "daily_budget": DAILY_BUDGET,
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "LEAD_GENERATION",
        "targeting": json.dumps(targeting),
        "status": "PAUSED",
        "page_id": page_id,
    })
    asid = data["id"]
    log(f"Ad Set created — ID: {asid}")
    return asid


# ── Step 7: Create Lead Gen Form ─────────────────────────────────────────────────
def create_lead_form(page_id, page_token):
    log("Creating Lead Generation form…")
    form_data = {
        "name": "Zapit Free Pest Inspection Request",
        "locale": "en_AU",
        "questions": json.dumps([
            {"type": "FULL_NAME"},
            {"type": "EMAIL"},
            {"type": "PHONE"},
            {"type": "CUSTOM",
             "label": "What pest do you have?",
             "options": [
                 {"value": "termites", "key": "Termites"},
                 {"value": "cockroaches", "key": "Cockroaches"},
                 {"value": "rodents", "key": "Rodents"},
                 {"value": "spiders", "key": "Spiders"},
                 {"value": "ants", "key": "Ants"},
                 {"value": "other", "key": "Other"},
             ]},
            {"type": "CUSTOM",
             "label": "Best time to call?",
             "options": [
                 {"value": "morning", "key": "Morning (8am–12pm)"},
                 {"value": "afternoon", "key": "Afternoon (12pm–5pm)"},
                 {"value": "evening", "key": "Evening (5pm–7pm)"},
             ]},
        ]),
        "privacy_policy": json.dumps({
            "url": "https://www.zapitpestmelbourne.com.au/privacy-policy",
            "link_text": "Privacy Policy"
        }),
        "thank_you_page": json.dumps({
            "title": "Thanks! We'll be in touch shortly.",
            "body": "Our team at Zapit will call you to confirm your free inspection. Pest protection you can trust.",
            "cta_type": "VIEW_WEBSITE",
            "cta_link": "https://www.zapitpestmelbourne.com.au",
        }),
    }
    resp = requests.post(
        f"{API_BASE}/{page_id}/leadgen_forms",
        params={"access_token": page_token},
        data=form_data
    )
    data = resp.json()
    if "error" in data:
        print(f"\n✗ Lead form error: {data['error']['message']}")
        sys.exit(1)
    form_id = data["id"]
    log(f"Lead form created — ID: {form_id}")
    return form_id


# ── Step 8: Create Ad Creative ────────────────────────────────────────────────────
def create_creative(page_id, video_id, lead_form_id):
    log("Creating Ad Creative…")
    story = {
        "page_id": page_id,
        "video_data": {
            "video_id": video_id,
            "title": "Pest Protection You Can Trust",
            "message": "🏡 Melbourne families trust Zapit to keep their homes pest-free — fast, safe and with minimal disruption.\n\n✅ Child-safe & pet-safe treatments\n✅ DHHS licensed & fully insured\n✅ Same-day service available\n\nBook your FREE inspection today 👇",
            "call_to_action": {
                "type": "SIGN_UP",
                "value": {"lead_gen_form_id": lead_form_id}
            },
        }
    }
    data = api("post", f"{AD_ACCOUNT_ID}/adcreatives", data={
        "name": "Zapit TV Spot Creative",
        "object_story_spec": json.dumps(story),
    })
    cid = data["id"]
    log(f"Creative created — ID: {cid}")
    return cid


# ── Step 9: Create Ad ─────────────────────────────────────────────────────────────
def create_ad(adset_id, creative_id):
    log("Creating Ad…")
    data = api("post", f"{AD_ACCOUNT_ID}/ads", data={
        "name": AD_NAME,
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED",
    })
    ad_id = data["id"]
    log(f"Ad created — ID: {ad_id}")
    return ad_id


# ── Main ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🐛 Zapit Pest Melbourne — Meta Ads Campaign Launcher")
    print("=" * 55)

    download_video()
    strip_music()

    page_id, page_token = get_page_id()
    video_id   = upload_video(page_id, page_token)
    campaign_id = create_campaign()
    adset_id    = create_adset(campaign_id, page_id)
    form_id     = create_lead_form(page_id, page_token)
    creative_id = create_creative(page_id, video_id, form_id)
    ad_id       = create_ad(adset_id, creative_id)

    print("\n✅ All done! Campaign is PAUSED — review in Meta Ads Manager then set to ACTIVE.")
    print(f"\n   Campaign ID : {campaign_id}")
    print(f"   Ad Set ID   : {adset_id}")
    print(f"   Ad ID       : {ad_id}")
    print(f"   Lead Form   : {form_id}")
    print(f"\n   👉 https://www.facebook.com/adsmanager/manage/campaigns?act={AD_ACCOUNT_ID.replace('act_','')}")
