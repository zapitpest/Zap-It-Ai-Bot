"""Utility functions for classifying and filtering incoming emails."""

import re

REAL_ESTATE_KEYWORDS = [
    "property manager", "property management", "real estate", "realty",
    "leasing", "rental", "landlord", "tenant", "tenancy",
    "ray white", "barry plant", "hockingstuart", "hocking stuart",
    "nelson alexander", "woodards", "jellis craig", "marshall white",
    "jas stephens", "stockdale", "cavalier", "first national",
    "ljhooker", "lj hooker", "century 21", "raine horne",
    "fletchers", "buxton", "broadhurst",
]

SKIP_KEYWORDS = [
    "unsubscribe", "marketing", "newsletter", "no-reply", "noreply",
    "do not reply", "donotreply", "promotion", "offer", "discount",
    "hipages",  # hipages leads are explicitly ignored
    "calendar invite", "ics attachment", "you have been invited",
]

WORK_ORDER_KEYWORDS = [
    "work order", "workorder", "service request", "pest control",
    "treatment required", "treatment request", "inspection required",
    "please arrange", "please organize", "please organise",
    "booking request", "job request",
]


def is_real_estate(email: dict) -> bool:
    text = " ".join([
        email.get("subject", ""),
        email.get("snippet", ""),
        email.get("from", ""),
        email.get("body", ""),
    ]).lower()
    return any(kw in text for kw in REAL_ESTATE_KEYWORDS)


def is_skip(email: dict) -> bool:
    text = " ".join([
        email.get("subject", ""),
        email.get("snippet", ""),
        email.get("from", ""),
        email.get("body", ""),
    ]).lower()
    return any(kw in text for kw in SKIP_KEYWORDS)


def is_work_order(email: dict) -> bool:
    text = " ".join([
        email.get("subject", ""),
        email.get("snippet", ""),
        email.get("body", ""),
    ]).lower()
    return any(kw in text for kw in WORK_ORDER_KEYWORDS)


def extract_address(text: str) -> str:
    """Best-effort address extraction from email body."""
    patterns = [
        r"\d+[\w\s]*(street|st|road|rd|avenue|ave|drive|dr|court|ct|place|pl|way|boulevard|blvd)[\w\s,]*",
        r"\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*,\s*[A-Z][a-z]+",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""


def extract_sender_name(email: dict) -> str:
    from_str = email.get("from", "")
    match = re.match(r'^"?([^"<]+)"?\s*<', from_str)
    if match:
        return match.group(1).strip().split()[0]
    return "there"
