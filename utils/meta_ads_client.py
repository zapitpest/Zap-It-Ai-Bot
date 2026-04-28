"""
Meta Ads Manager API client.

Used to: track ad campaign performance, pull lead form submissions,
and sync new leads from Facebook/Instagram ads into GoHighLevel CRM.

API reference: https://developers.facebook.com/docs/marketing-api
Auth: Access token (META_ADS_TOKEN from .env)
      Ad Account ID (META_AD_ACCOUNT_ID from .env) — format: act_XXXXXXXXX
"""

import logging
import requests
from config import META_ADS_TOKEN, META_AD_ACCOUNT_ID

logger = logging.getLogger(__name__)

META_BASE = "https://graph.facebook.com/v19.0"


def _get(endpoint: str, params: dict = None) -> dict:
    p = {"access_token": META_ADS_TOKEN, **(params or {})}
    r = requests.get(f"{META_BASE}/{endpoint}", params=p, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(endpoint: str, data: dict) -> dict:
    data["access_token"] = META_ADS_TOKEN
    r = requests.post(f"{META_BASE}/{endpoint}", data=data, timeout=15)
    r.raise_for_status()
    return r.json()


# --- Account & Campaigns ---

def get_account() -> dict:
    """Return basic info about the ad account."""
    return _get(META_AD_ACCOUNT_ID, {"fields": "id,name,account_status,currency,timezone_name"})


def list_campaigns(status: str = "ACTIVE") -> list:
    """List campaigns. status: ACTIVE | PAUSED | ARCHIVED | ALL"""
    params = {
        "fields": "id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time",
        "effective_status": f'["{status}"]' if status != "ALL" else '["ACTIVE","PAUSED","ARCHIVED"]',
    }
    return _get(f"{META_AD_ACCOUNT_ID}/campaigns", params).get("data", [])


def get_campaign_insights(campaign_id: str, date_preset: str = "last_7d") -> dict:
    """Get performance metrics for a campaign."""
    params = {
        "fields": "impressions,clicks,spend,cpc,ctr,reach,leads,actions",
        "date_preset": date_preset,
    }
    data = _get(f"{campaign_id}/insights", params).get("data", [])
    return data[0] if data else {}


def get_account_insights(date_preset: str = "last_7d") -> dict:
    """Get overall account performance metrics."""
    params = {
        "fields": "impressions,clicks,spend,cpc,ctr,reach,actions",
        "date_preset": date_preset,
    }
    data = _get(f"{META_AD_ACCOUNT_ID}/insights", params).get("data", [])
    return data[0] if data else {}


# --- Lead Forms ---

def list_lead_forms(page_id: str = "") -> list:
    """List all lead gen forms for the page."""
    pid = page_id or META_AD_ACCOUNT_ID
    return _get(f"{pid}/leadgen_forms", {"fields": "id,name,status,leads_count"}).get("data", [])


def get_leads(form_id: str, limit: int = 100) -> list:
    """Fetch lead submissions from a form."""
    params = {
        "fields": "id,created_time,field_data",
        "limit": limit,
    }
    return _get(f"{form_id}/leads", params).get("data", [])


def parse_lead(lead: dict) -> dict:
    """Convert raw lead field_data into a flat dict."""
    result = {
        "id": lead.get("id", ""),
        "created_time": lead.get("created_time", ""),
    }
    for field in lead.get("field_data", []):
        key = field.get("name", "").lower().replace(" ", "_")
        values = field.get("values", [])
        result[key] = values[0] if values else ""
    return result


def get_new_leads(form_id: str, since_timestamp: str = "") -> list:
    """
    Fetch leads, optionally filtered to those created after since_timestamp.
    since_timestamp: ISO8601 string e.g. '2024-01-01T00:00:00+0000'
    """
    params = {
        "fields": "id,created_time,field_data",
        "limit": 100,
    }
    if since_timestamp:
        params["filtering"] = f'[{{"field":"time_created","operator":"GREATER_THAN","value":"{since_timestamp}"}}]'

    raw = _get(f"{form_id}/leads", params).get("data", [])
    return [parse_lead(lead) for lead in raw]


# --- Ad Sets & Ads ---

def list_ad_sets(campaign_id: str) -> list:
    params = {"fields": "id,name,status,daily_budget,targeting,start_time"}
    return _get(f"{campaign_id}/adsets", params).get("data", [])


def list_ads(ad_set_id: str) -> list:
    params = {"fields": "id,name,status,creative,effective_status"}
    return _get(f"{ad_set_id}/ads", params).get("data", [])
