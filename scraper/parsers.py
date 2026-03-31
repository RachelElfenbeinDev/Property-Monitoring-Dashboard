"""
Parsing logic for extracting case details from HTML.

This module contains functions for extracting specific fields
from the property complaint case detail pages.
"""

from bs4 import BeautifulSoup


def extract_complaint_text_from_soup(soup: BeautifulSoup) -> str:
    """Extract complaint nature/description from the detail page.

    Looks for the specific span element containing the complaint text.

    Args:
        soup: BeautifulSoup object of the case detail HTML.

    Returns:
        Complaint text, or empty string if not found.
    """
    complaint_span = soup.find("span", id="lblComplaintNature")
    return complaint_span.get_text(" ", strip=True) if complaint_span else ""


def extract_case_timeline_from_soup(soup: BeautifulSoup) -> list[dict]:
    """Extract the timeline of case status events.

    Parses the case timeline table to extract chronological events.
    Handles both dgDisplayDates2 and dgDisplayDates table IDs for
    backward compatibility.

    Args:
        soup: BeautifulSoup object of the case detail HTML.

    Returns:
        List of event dictionaries with 'date' and 'status' keys.
    """
    table = soup.find("table", id="dgDisplayDates2")
    if table is None:
        table = soup.find("table", id="dgDisplayDates")

    if table is None:
        return []

    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")

    events: list[dict] = []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        date_text = cells[0].get_text(strip=True)
        status_text = cells[1].get_text(strip=True)

        if date_text and status_text:
            events.append(
                {
                    "date": date_text,
                    "status": status_text,
                }
            )

    return events


def parse_case_detail(html: str, detail_url: str) -> dict:
    """Parse a case detail HTML page into structured data.

    Args:
        html: Raw HTML content of the case detail page.
        detail_url: The URL of the case detail page.

    Returns:
        Dictionary containing extracted case details:
        - complaint_text: The complaint description
        - events: List of status events
        - detail_url: The case detail URL
    """
    soup = BeautifulSoup(html, "html.parser")

    return {
        "detail_url": detail_url,
        "complaint_text": extract_complaint_text_from_soup(soup),
        "events": extract_case_timeline_from_soup(soup),
    }
