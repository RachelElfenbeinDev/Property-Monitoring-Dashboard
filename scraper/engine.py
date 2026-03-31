"""
Scraper engine for fetching HTML content from the property database.

This module handles HTTP requests to the housing authority website and
provides methods for fetching case lists and case details.
"""

import threading
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Base URL templates - APN is injected dynamically
MAIN_URL_TEMPLATE = (
    "https://housingapp.lacity.org/reportviolation/Pages/"
    "PropAtivityCases?APN={apn}&Source=ActivityReport"
)

BASE_DETAIL_URL_TEMPLATE = (
    "https://housingapp.lacity.org/reportviolation/Pages/"
    "PublicPropertyActivityReport?APN={apn}&CaseType=1&CaseNo={case_no}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    )
}

_thread_local = threading.local()


def validate_apn(apn: str) -> bool:
    """Validate APN format - must be exactly 10 digits.

    Args:
        apn: The APN string to validate.

    Returns:
        True if APN is valid (10 digits), False otherwise.
    """
    if not apn:
        return False
    return apn.strip().isdigit() and len(apn.strip()) == 10


def get_session() -> requests.Session:
    """Get a thread-local HTTP session for making requests.

    Uses thread-local storage to maintain separate sessions per thread,
    which is important for concurrent operations.

    Returns:
        A requests.Session object with headers pre-configured.
    """
    session = getattr(_thread_local, "session", None)

    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)
        _thread_local.session = session

    return session


def load_html(url: str) -> str:
    """Fetch HTML content from a URL.

    Args:
        url: The URL to fetch.

    Returns:
        HTML content as a string.

    Raises:
        requests.HTTPError: If the request fails.
        requests.Timeout: If the request times out.
    """
    response = get_session().get(url, timeout=(10, 30))
    response.raise_for_status()
    return response.text


def load_property_cases_page(apn: str) -> str:
    """Fetch the main property cases page for a given APN.

    Args:
        apn: The 10-digit Assessor Parcel Number.

    Returns:
        HTML content of the main cases page.

    Raises:
        ValueError: If APN format is invalid.
    """
    if not validate_apn(apn):
        raise ValueError(f"Invalid APN format: {apn}. APN must be exactly 10 digits.")

    url = MAIN_URL_TEMPLATE.format(apn=apn.strip())
    return load_html(url)


# def extract_cases_from_main_page(html: str) -> list[dict]:
#     """Extract case listings from the main cases page HTML.

#     Parses the HTML table (dgPropCases2) to extract basic case information.

#     Args:
#         html: HTML content of the main cases page.

#     Returns:
#         List of case dictionaries with case_type, case_number, date_closed, etc.

#     Raises:
#         ValueError: If the expected table structure is not found.
#     """
#     soup = BeautifulSoup(html, "html.parser")

#     table = soup.find("table", id="dgPropCases2")
#     if table is None:
#         raise ValueError("Table dgPropCases2 not found")

#     tbody = table.find("tbody")
#     if tbody is None:
#         raise ValueError("tbody not found in table")

#     results: list[dict] = []

#     for row in tbody.find_all("tr"):
#         cells = row.find_all("td")
#         if len(cells) < 4:
#             continue

#         action_cell = cells[0]
#         case_type = cells[1].get_text(strip=True)
#         case_number = cells[2].get_text(strip=True)
#         date_closed = cells[3].get_text(strip=True)

#         link = action_cell.find("a")
#         select_id = link.get("id", "") if link else ""
#         select_href = link.get("href", "") if link else ""

#         results.append(
#             {
#                 "case_type": case_type,
#                 "case_number": case_number,
#                 "date_closed": date_closed,
#                 "select_id": select_id,
#                 "select_href": select_href,
#             }
#         )

#     return results
def extract_cases_from_main_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", id="dgPropCases2")
    if table is None:
        raise ValueError("Table dgPropCases2 not found")

    tbody = table.find("tbody")
    if tbody is None:
        raise ValueError("tbody not found in table")

    results: list[dict] = []

    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        action_cell = cells[0]
        case_type = cells[1].get_text(strip=True)
        case_number = cells[2].get_text(strip=True)
        date_closed_raw = cells[3].get_text(strip=True)

        # &nbsp; מגיע כ-\xa0 — ריק = פתוח
        date_closed = "" if date_closed_raw in ("\xa0", "&nbsp;", "") else date_closed_raw

        if not case_number:
            continue

        link = action_cell.find("a")
        select_id = link.get("id", "") if link else ""
        select_href = link.get("href", "") if link else ""

        results.append({
            "case_type": case_type,
            "case_number": case_number,
            "date_closed": date_closed,
            "select_id": select_id,
            "select_href": select_href,
        })

    return results

def build_case_detail_url(case_no: str, apn: str) -> str:
    """Build the URL for a specific case detail page.

    Args:
        case_no: The case number.
        apn: The property APN.

    Returns:
        Full URL to the case detail page.
    """
    return BASE_DETAIL_URL_TEMPLATE.format(apn=apn.strip(), case_no=case_no)


def fetch_case_detail(case_number: str, apn: str) -> dict:
    """Fetch detailed information for a specific case.

    Args:
        case_number: The case number to fetch details for.
        apn: The property APN.

    Returns:
        Dictionary containing case detail information.

    Raises:
        ValueError: If case details cannot be parsed.
    """
    url = build_case_detail_url(case_number, apn)
    html = load_html(url)

    # Import here to avoid circular imports
    from scraper.parsers import parse_case_detail

    return parse_case_detail(html, url)
