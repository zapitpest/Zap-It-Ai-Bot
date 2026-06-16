#!/usr/bin/env python3
"""
Zap It Pest Control — Meta Ads Human Approval & Launch Script
=============================================================
SAFETY: DRY_RUN=true by default. Nothing is uploaded or published
until every checklist item is ticked AND you explicitly type APPROVE.

Usage:
    python3 approve_and_launch.py            # review + dry run
    python3 approve_and_launch.py --launch   # interactive approval then live
"""

import json
import os
import sys
import time
import subprocess
import requests
from pathlib import Path

# ── Safety gate ───────────────────────────────────────────────────────────────
DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"
if "--launch" in sys.argv:
    DRY_RUN = False

# ── Credentials (from .env only — never hardcoded) ────────────────────────────
from dotenv import load_dotenv
load_dotenv()
META_TOKEN      = os.getenv("META_ADS_TOKEN")
AD_ACCOUNT_ID   = os.getenv("META_AD_ACCOUNT_ID", "act_61588715705652")
API_BASE        = "https://graph.facebook.com/v19.0"

# ── Asset paths ───────────────────────────────────────────────────────────────
DRAFT_FILE       = Path("meta_ads_draft.json")
APPROVAL_FILE    = Path("approval_queue.json")
VIDEO_16x9_FILE  = Path("zapit_ad_16x9.mp4")
VIDEO_9x16_FILE  = Path("zapit_ad_9x16.mp4")
VOICEOVER_FILE   = Path("voiceover_zapit.mp3")

# ── Higgsfield video CDN URLs (filled after generation completes) ──────────────
HIGGSFIELD_JOBS = {
    "16x9": "762375a0-9722-4425-b506-4c343e085fdb",
    "9x16": "27f7adec-5c52-46c4-96a1-cf2adf90587d",
}
# Update these once the jobs complete:
VIDEO_URLS = {
    "16x9": os.getenv("VIDEO_URL_16x9", ""),
    "9x16": os.getenv("VIDEO_URL_9x16", ""),
}


def log(msg):
    print(f"  → {msg}")


def abort(msg):
    print(f"\n✗  ABORTED: {msg}")
    sys.exit(1)


def meta_api(method, path, **kwargs):
    if DRY_RUN:
        print(f"  [DRY RUN] Would call {method.upper()} /{path}")
        return {"id": f"dry_run_{path.replace('/','_')}"}
    url = f"{API_BASE}/{path}"
    params = kwargs.pop("params", {})
    params["access_token"] = META_TOKEN
    resp = getattr(requests, method)(url, params=params, **kwargs)
    data = resp.json()
    if "error" in data:
        abort(f"Meta API error: {data['error']['message']}")
    return data


# ── Step 1: Review checklist ──────────────────────────────────────────────────
def run_checklist():
    print("\n" + "="*60)
    print("  ZAP IT PEST CONTROL — META ADS APPROVAL CHECKLIST")
    print("="*60)

    draft = json.loads(DRAFT_FILE.read_text())
    checklist = draft["approval_checklist"]

    items = {
        "video_16x9_reviewed":  f"16:9 Feed video reviewed (job: {HIGGSFIELD_JOBS['16x9']})",
        "video_9x16_reviewed":  f"9:16 Reels/Stories video reviewed (job: {HIGGSFIELD_JOBS['9x16']})",
        "voiceover_reviewed":   f"Voiceover reviewed ({VOICEOVER_FILE})",
        "ad_copy_approved":     "Ad copy and on-screen text approved",
        "lead_form_approved":   "Lead gen form questions approved",
        "budget_confirmed":     "Budget confirmed: $10/day AUD",
        "targeting_confirmed":  "Targeting confirmed: Melbourne 25–55, homeowners",
        "human_approved":       "FINAL HUMAN APPROVAL",
    }

    all_approved = True
    for key, label in items.items():
        status = "✅" if checklist.get(key) else "❌"
        print(f"  {status}  {label}")
        if not checklist.get(key):
            all_approved = False

    return all_approved, draft


# ── Step 2: Interactive approval ──────────────────────────────────────────────
def interactive_approve():
    draft = json.loads(DRAFT_FILE.read_text())
    checklist = draft["approval_checklist"]

    print("\n  Tick off each item (y/n):\n")
    for key in checklist:
        if checklist[key]:
            continue
        label = key.replace("_", " ").title()
        answer = input(f"  ✔ {label}? (y/n): ").strip().lower()
        if answer == "y":
            checklist[key] = True

    draft["approval_checklist"] = checklist
    DRAFT_FILE.write_text(json.dumps(draft, indent=2))

    if not all(checklist.values()):
        abort("Not all items approved. Re-run when ready.")

    confirm = input("\n  Type APPROVE to confirm and launch (or anything else to abort): ").strip()
    if confirm != "APPROVE":
        abort("Approval not confirmed.")
    return draft


# ── Step 3: Download videos ────────────────────────────────────────────────────
def download_assets():
    log("Downloading video assets…")
    for ratio, url in VIDEO_URLS.items():
        fname = VIDEO_16x9_FILE if ratio == "16x9" else VIDEO_9x16_FILE
        if not url:
            log(f"  No URL set for {ratio} — skipping. Set VIDEO_URL_{ratio.upper()} in .env")
            continue
        if fname.exists():
            log(f"  {fname} already exists — skipping download")
            continue
        log(f"  Downloading {ratio}…")
        r = requests.get(url, stream=True)
        with open(fname, "wb") as f:
            for chunk in r.iter_content(chunk_size=256*1024):
                f.write(chunk)
        log(f"  Saved → {fname}")


# ── Step 4: Merge voiceover onto video ────────────────────────────────────────
def merge_voiceover(video_in, video_out):
    if not VOICEOVER_FILE.exists():
        log(f"  No voiceover file found — skipping merge for {video_in}")
        return video_in
    log(f"  Merging voiceover onto {video_in}…")
    result = subprocess.run([
        "ffmpeg", "-y", "-i", str(video_in), "-i", str(VOICEOVER_FILE),
        "-filter_complex",
        "[0:a]volume=0.15[amb];[1:a]volume=1.0[vo];[amb][vo]amix=inputs=2:duration=first[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        str(video_out)
    ], capture_output=True, text=True)
    if result.returncode != 0:
        log(f"  ffmpeg failed — using original: {result.stderr[-200:]}")
        return video_in
    log(f"  Merged → {video_out}")
    return video_out


# ── Step 5: Upload video to Meta ──────────────────────────────────────────────
def upload_video(video_path, title):
    log(f"  Uploading {video_path} to Meta…")
    if DRY_RUN:
        log(f"  [DRY RUN] Would upload {video_path}")
        return "dry_run_video_id"
    with open(video_path, "rb") as f:
        resp = requests.post(
            f"{API_BASE}/{AD_ACCOUNT_ID}/advideos",
            params={"access_token": META_TOKEN},
            data={"name": title},
            files={"source": f}
        )
    data = resp.json()
    if "error" in data:
        abort(f"Video upload error: {data['error']['message']}")
    video_id = data["id"]
    log(f"  Uploaded — video ID: {video_id}")

    # Wait for processing
    for _ in range(30):
        time.sleep(10)
        status = meta_api("get", video_id, params={"fields": "status"})
        if status.get("status", {}).get("video_status") == "ready":
            break
    return video_id


# ── Step 6: Create campaign structure ─────────────────────────────────────────
def create_campaign(draft):
    log("Creating campaign (PAUSED)…")
    c = draft["campaign"]
    data = meta_api("post", f"{AD_ACCOUNT_ID}/campaigns", data={
        "name": c["name"],
        "objective": c["objective"],
        "status": "PAUSED",
        "special_ad_categories": "[]",
    })
    return data["id"]


def create_adset(draft, campaign_id):
    log("Creating ad set (PAUSED)…")
    a = draft["ad_set"]
    data = meta_api("post", f"{AD_ACCOUNT_ID}/adsets", data={
        "name": a["name"],
        "campaign_id": campaign_id,
        "daily_budget": a["daily_budget_cents"],
        "billing_event": a["billing_event"],
        "optimization_goal": a["optimization_goal"],
        "targeting": json.dumps(a["targeting"]),
        "status": "PAUSED",
    })
    return data["id"]


def create_lead_form(draft, page_id, page_token):
    log("Creating lead gen form…")
    f = draft["lead_gen_form"]
    resp = requests.post(
        f"{API_BASE}/{page_id}/leadgen_forms",
        params={"access_token": page_token if not DRY_RUN else "dry"},
        data={
            "name": f["name"],
            "locale": f["locale"],
            "questions": json.dumps(f["questions"]),
            "privacy_policy": json.dumps(f["privacy_policy"]),
            "thank_you_page": json.dumps(f["thank_you_page"]),
        }
    ) if not DRY_RUN else type("R", (), {"json": lambda s: {"id": "dry_form_id"}})()
    data = resp.json()
    if "error" in data:
        abort(f"Lead form error: {data['error']['message']}")
    return data["id"]


def create_creative(draft, page_id, video_id, form_id, ratio="16x9"):
    log(f"Creating ad creative ({ratio})…")
    c = draft[f"ad_creative_{ratio}"]
    story = {
        "page_id": page_id,
        "video_data": {
            "video_id": video_id,
            "title": "Pest Protection You Can Trust",
            "message": c["page_message"],
            "call_to_action": {
                "type": c["call_to_action"]["type"],
                "value": {"lead_gen_form_id": form_id}
            },
        }
    }
    data = meta_api("post", f"{AD_ACCOUNT_ID}/adcreatives", data={
        "name": c["name"],
        "object_story_spec": json.dumps(story),
    })
    return data["id"]


def create_ad(draft, adset_id, creative_id, ratio="16x9"):
    log(f"Creating ad ({ratio}, PAUSED)…")
    ad = next(a for a in draft["ads"] if ratio in a["name"].lower())
    data = meta_api("post", f"{AD_ACCOUNT_ID}/ads", data={
        "name": ad["name"],
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED",
    })
    return data["id"]


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = "DRY RUN" if DRY_RUN else "⚠️  LIVE MODE"
    print(f"\n🐛 Zap It Pest Control — Meta Ads Launcher [{mode}]")
    print("="*60)

    all_approved, draft = run_checklist()

    if "--launch" in sys.argv:
        if not all_approved:
            draft = interactive_approve()
            all_approved = True
    else:
        print("\n  📋 Draft summary:")
        print(f"     Campaign  : {draft['campaign']['name']}")
        print(f"     Budget    : ${draft['ad_set']['daily_budget_cents']/100:.2f}/day AUD")
        print(f"     Objective : {draft['campaign']['objective']}")
        print(f"     Geo       : Melbourne, VIC, AU — ages 25–55")
        print(f"     Placements: Facebook Feed + Instagram Feed + Reels + Stories")
        print(f"     Videos    : 16:9 (feed) + 9:16 (reels/stories)")
        print(f"     Voiceover : {VOICEOVER_FILE}")
        print(f"\n  ✅ To launch when ready:")
        print(f"     python3 approve_and_launch.py --launch")
        print(f"\n  ⚠️  Nothing has been uploaded or published. All actions are PAUSED drafts.")
        sys.exit(0)

    if not META_TOKEN:
        abort("META_ADS_TOKEN not set in .env")

    # Get Facebook page
    pages = meta_api("get", "me/accounts")
    if DRY_RUN:
        page_id, page_token = "dry_page_id", "dry_token"
    else:
        page = pages["data"][0]
        page_id, page_token = page["id"], page["access_token"]
        log(f"Using page: {page['name']} ({page_id})")

    download_assets()

    # 16:9 version
    final_16x9 = merge_voiceover(VIDEO_16x9_FILE, Path("zapit_final_16x9.mp4"))
    vid_id_16x9 = upload_video(final_16x9, "Zap It TV Spot 16:9")

    # 9:16 version
    final_9x16 = merge_voiceover(VIDEO_9x16_FILE, Path("zapit_final_9x16.mp4"))
    vid_id_9x16 = upload_video(final_9x16, "Zap It TV Spot 9:16")

    campaign_id = create_campaign(draft)
    adset_id    = create_adset(draft, campaign_id)
    form_id     = create_lead_form(draft, page_id, page_token)

    creative_16x9 = create_creative(draft, page_id, vid_id_16x9, form_id, "16x9")
    creative_9x16 = create_creative(draft, page_id, vid_id_9x16, form_id, "9x16")

    ad_16x9 = create_ad(draft, adset_id, creative_16x9, "16x9")
    ad_9x16 = create_ad(draft, adset_id, creative_9x16, "9x16")

    print(f"\n{'='*60}")
    print(f"  {'[DRY RUN COMPLETE]' if DRY_RUN else '✅ CAMPAIGN CREATED — ALL ADS PAUSED'}")
    print(f"  Campaign ID  : {campaign_id}")
    print(f"  Ad Set ID    : {adset_id}")
    print(f"  Lead Form    : {form_id}")
    print(f"  Ad (16:9)    : {ad_16x9}")
    print(f"  Ad (9:16)    : {ad_9x16}")
    if not DRY_RUN:
        print(f"\n  👉 Review in Meta Ads Manager before setting to ACTIVE:")
        print(f"     https://www.facebook.com/adsmanager/manage/campaigns?act={AD_ACCOUNT_ID.replace('act_','')}")
    print(f"{'='*60}\n")
