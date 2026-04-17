"""ServiceM8 API client. Auth via x-api-key header only — never use Basic auth."""

import requests
from config import SM8_BASE_URL, SM8_HEADERS


def _url(endpoint: str) -> str:
    return f"{SM8_BASE_URL}/{endpoint.lstrip('/')}"


def get(endpoint: str, params: dict = None) -> list | dict:
    resp = requests.get(_url(endpoint), headers=SM8_HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def post(endpoint: str, data: dict) -> dict:
    resp = requests.post(_url(endpoint), headers=SM8_HEADERS, json=data)
    resp.raise_for_status()
    return resp.json()


def put(endpoint: str, data: dict) -> dict:
    resp = requests.put(_url(endpoint), headers=SM8_HEADERS, json=data)
    resp.raise_for_status()
    return resp.json()


# --- Companies ---

def create_company(name: str, address: str = "", **kwargs) -> dict:
    return post("company.json", {"name": name, "address": address, **kwargs})


def get_companies() -> list:
    return get("company.json")


def get_company(uuid: str) -> dict:
    return get(f"company/{uuid}.json")


# --- Contacts ---

def create_contact(company_uuid: str, first_name: str, last_name: str,
                   email: str = "", phone: str = "", **kwargs) -> dict:
    return post("companycontact.json", {
        "company_uuid": company_uuid,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        **kwargs,
    })


def get_contacts(company_uuid: str = None) -> list:
    params = {"%24filter": f"company_uuid eq '{company_uuid}'"} if company_uuid else None
    return get("companycontact.json", params)


# --- Jobs ---

def create_job(company_uuid: str, status: str = "Quote",
               description: str = "", **kwargs) -> dict:
    return post("job.json", {
        "company_uuid": company_uuid,
        "status": status,
        "description": description,
        **kwargs,
    })


def get_jobs(status: str = None) -> list:
    params = None
    if status:
        params = {"%24filter": f"status eq '{status}'"}
    return get("job.json", params)


def get_job(uuid: str) -> dict:
    return get(f"job/{uuid}.json")


def update_job(uuid: str, data: dict) -> dict:
    return put(f"job/{uuid}.json", data)


def complete_job(uuid: str) -> dict:
    return update_job(uuid, {"status": "Completed"})


def get_completed_jobs_since(hours: int = 24) -> list:
    """Return jobs completed within the last `hours` hours."""
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    all_jobs = get("job.json", {
        "%24filter": f"status eq 'Completed' and edit_date gt '{cutoff_str}'"
    })
    return all_jobs if isinstance(all_jobs, list) else []


# --- Job Materials (line items / invoice) ---

def add_material(job_uuid: str, name: str, quantity: float,
                 price: float, tax_rate_uuid: str = "", **kwargs) -> dict:
    return post("jobmaterial.json", {
        "job_uuid": job_uuid,
        "name": name,
        "quantity": quantity,
        "price": price,
        "displayed_amount": price * quantity,
        "tax_rate_uuid": tax_rate_uuid,
        **kwargs,
    })


def get_materials(job_uuid: str) -> list:
    return get("jobmaterial.json", {
        "%24filter": f"job_uuid eq '{job_uuid}'"
    })


# --- Job Activities (scheduling / technician assignment) ---

def assign_technician(job_uuid: str, staff_uuid: str,
                      start_date: str, end_date: str) -> dict:
    """start_date / end_date format: 'YYYY-MM-DD HH:MM:SS'"""
    return post("jobactivity.json", {
        "job_uuid": job_uuid,
        "staff_uuid": staff_uuid,
        "start_date": start_date,
        "end_date": end_date,
    })


# --- Staff ---

def get_staff() -> list:
    return get("staff.json")


# --- Tax Rates ---

def get_tax_rates() -> list:
    return get("taxrate.json")


# --- Form Responses ---

def get_form_responses(job_uuid: str) -> list:
    return get("formresponse.json", {
        "%24filter": f"job_uuid eq '{job_uuid}'"
    })


# --- Job Contacts ---

def get_job_contacts(job_uuid: str) -> list:
    return get("jobcontact.json", {
        "%24filter": f"job_uuid eq '{job_uuid}'"
    })
