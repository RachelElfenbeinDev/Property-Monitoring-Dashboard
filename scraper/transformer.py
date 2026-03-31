"""
Case enrichment logic for enhancing case data with details and priority.

This module handles enriching basic case data with detailed information
and calculating priority levels based on case status.
"""

from datetime import datetime
from typing import Callable, Optional


def enrich_case(
    case: dict,
    fetch_func: Callable,
    is_active_func: Callable,
) -> dict:
    """Enrich a case with detailed information from the API.

    Fetches case details including complaint text, events, and URL.
    Only fetches details for active cases.

    Args:
        case: Basic case dictionary to enrich.
        fetch_func: Callable that fetches case detail data.
        is_active_func: Callable that determines if case is active.

    Returns:
        Enriched case dictionary with details, events, and priority.
    """
    case["complaint_text"] = ""
    case["events"] = []
    case["priority"] = "Low"
    case["last_status"] = "Closed"
    case["detail_url"] = ""
    case["previous_status"] = ""


    if not is_active_func(case):
        return case

    try:
        detail = fetch_func(case["case_number"])
        case["complaint_text"] = detail["complaint_text"]
        case["events"] = detail["events"]
        case["detail_url"] = detail["detail_url"]
        case["priority"] = calculate_priority(detail["events"])
        case["last_status"] = (
            detail["events"][0].get("status", "") if detail["events"] else ""
        )
    except Exception as exc:
        case["priority"] = "Unknown"
        case["error"] = str(exc)

    return case


def parse_event_date(date_str: str) -> Optional[datetime]:
    """Parse a date string from various supported formats.

    Attempts to parse using multiple common date/time formats.

    Args:
        date_str: Date string to parse.

    Returns:
        Parsed datetime object, or None if parsing fails.
    """
    formats = [
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    return None


def calculate_priority(events: list[dict]) -> str:
    """Calculate case priority based on most recent status event.

    Uses predefined sets of statuses for High, Medium, and Low priority.
    Returns "Unknown" if no status can be determined.

    Args:
        events: List of event dictionaries with 'status' keys.

    Returns:
        Priority level: "High", "Medium", "Low", or "Unknown".
    """
    if not events:
        return "Unknown"

    last_status = events[0].get("status", "")

    high_statuses = {
        "Referred to Enforcement Section",
        "Referred to City Attorney",
        "Notice of General Manager Hearing",
        "Order Issued to Property Owner",
        "Complaint Received",
        "City Council Action for Rent Escrow Account Program Removal",
    }

    medium_statuses = {
        "Senior Inspector Appeal Received",
        "Notice Of Acceptance Mail Sent",
        "Site Visit/Initial Inspection",
        "Site Visit/Compliance Inspection",
        "Photos",
        "Positive Outreach Report Date",
        "Schedule Council Removal Date",
    }

    low_statuses = {
        "All Violations Resolved Date",
        "Violations Corrected",
        "Compliance Date",
        "Complaint Closed",
        "No Violations Observed",
        "Escrow Account Closed",
        "Rent Escrow Account Program Close Date",
    }

    if last_status in high_statuses:
        return "High"
    if last_status in medium_statuses:
        return "Medium"
    if last_status in low_statuses:
        return "Low"

    return "Unknown"
