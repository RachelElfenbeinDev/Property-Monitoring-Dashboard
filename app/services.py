"""
Business logic and data services for case management.

This module contains all business logic for syncing cases, applying data rules,
and managing case status. The "Closed cases are viewed" rule is implemented here.
"""

import datetime
import sqlite3
from typing import Optional

from app.models import get_db_connection


REFRESH_INTERVAL_SECONDS = 2 * 60 * 60  # 2 hours


def parse_date(date_str: str) -> Optional[datetime.date]:
    """Parse a date string in MM/DD/YYYY format.

    Args:
        date_str: Date string to parse.

    Returns:
        Parsed date object or None if parsing fails.
    """
    if not date_str or not date_str.strip():
        return None

    try:
        return datetime.datetime.strptime(date_str.strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def is_case_active(case: dict) -> bool:
    """Determine if a case is still active (not closed or closed date is in future).

    Args:
        case: Dictionary containing case data.

    Returns:
        True if case is active, False if closed.
    """
    date_closed_str = (case.get("date_closed") or "").strip()

    if not date_closed_str:
        return True

    parsed_date = parse_date(date_closed_str)
    if parsed_date is None:
        return True

    return parsed_date > datetime.date.today()


def get_case_last_status(case: dict) -> str:
    """Extract the most recent status from a case.

    For cases with events, returns the status of the most recent event.
    For cases without events but with a date_closed, returns "Closed".

    Args:
        case: Dictionary containing case data.

    Returns:
        Status string, or empty string if no status found.
    """
    events = case.get("events") or []
    if events:
        # events[0] is the newest event
        return (events[0].get("status") or "").strip()

    if (case.get("date_closed") or "").strip():
        return "Closed"

    return ""


def get_saved_status_map(apn: Optional[str] = None) -> dict[str, dict]:
    """Get a map of saved cases with their status and view state.

    Args:
        apn: Optional APN to filter cases by. If None, returns all cases.

    Returns:
        Dictionary mapping case_number -> {'last_status': str, 'is_viewed': bool}.
    """
    with get_db_connection() as conn:
        if apn:
            rows = conn.execute(
                "SELECT case_number, last_status, is_viewed FROM property_cases WHERE apn = ?",
                (apn,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT case_number, last_status, is_viewed FROM property_cases"
            ).fetchall()

    return {
        row["case_number"]: {
            "last_status": row["last_status"],
            "is_viewed": bool(row["is_viewed"]),
        }
        for row in rows
    }


def is_case_closed(case_status: str) -> bool:
    """Check if a case status indicates the case is closed.

    This is a KEY function for the "Closed cases are viewed" rule.
    When a case is closed, it's automatically marked as viewed.

    Args:
        case_status: Status string to check.

    Returns:
        True if status indicates case is closed.
    """
    closed_statuses = {
        "All Violations Resolved Date",
        "Violations Corrected",
        "Complaint Closed",
        "No Violations Observed",
        "Escrow Account Closed",
        "Rent Escrow Account Program Close Date",
    }
    return (
        case_status in closed_statuses
        or "Closed" in case_status
        or "Resolved" in case_status
    )


def apply_data_sync_rules(cases: list[dict], apn: Optional[str] = None) -> None:
    """Apply data synchronization rules to determine is_viewed flag.

    CRITICAL BUSINESS LOGIC:
    - Rule A: New cases -> is_viewed = False
    - Rule B: Updated cases (status changed) -> is_viewed = False
    - Rule C: CLOSED cases -> is_viewed = True (OVERRIDES Rules A & B)
    - Rule D: No changes -> preserve existing is_viewed value

    This function modifies the cases list in-place.

    Args:
        cases: List of case dictionaries to apply rules to.
        apn: Optional APN to filter saved cases for data sync rules.
    """
    saved_status_map = get_saved_status_map(apn)

    for case in cases:
        case_number = case["case_number"]
        current_status = case.get("last_status") or get_case_last_status(case)
        saved_record = saved_status_map.get(case_number)

        # Determine if case is new or updated
        is_new = case_number not in saved_status_map
        is_updated = saved_record and saved_record["last_status"] != current_status

        # Rule C: Closed cases always marked as viewed (takes precedence over all)
        if is_case_closed(current_status):
            case["is_viewed"] = True
        # Rule A: New cases
        elif is_new:
            case["is_viewed"] = False
        # Rule B: Updated cases
        elif is_updated:
            case["is_viewed"] = False
        # Rule D: No changes - preserve existing is_viewed value
        else:
            case["is_viewed"] = (
                saved_record.get("is_viewed", False) if saved_record else False
            )


def annotate_changes(cases: list[dict], apn: Optional[str] = None) -> None:
    saved_status_map = get_saved_status_map(apn)

    for case in cases:
        case_number = case["case_number"]
        current_status = case.get("last_status") or get_case_last_status(case)
        previous_status = (
            saved_status_map.get(case_number, {}).get("last_status")
            if saved_status_map.get(case_number)
            else None
        )

        case["last_status"] = current_status
        case["previous_status"] = previous_status or ""


def save_cases(cases: list[dict], apn: Optional[str] = None) -> None:
    """Save or update cases in the database.

    Applies data sync rules before saving. All cases are stamped with
    the current UTC timestamp.

    Args:
        cases: List of case dictionaries to save.
        apn: Optional APN to associate with the cases being saved.
    """
    batch_updated_at = datetime.datetime.utcnow().isoformat() + "Z"

    # Apply sync rules for is_viewed flag
    apply_data_sync_rules(cases, apn)

    with get_db_connection() as conn:
        for case in cases:
          conn.execute(
            """
            INSERT OR REPLACE INTO property_cases (
                case_number,
                apn,
                case_type,
                date_closed,
                last_status,
                previous_status,
                priority,
                complaint_text,
                detail_url,
                updated_at,
                is_viewed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case["case_number"],
                apn,
                case.get("case_type", ""),
                case.get("date_closed", ""),
                case.get("last_status") or get_case_last_status(case),
                case.get("previous_status", ""),
                case.get("priority", ""),
                case.get("complaint_text", ""),
                case.get("detail_url", ""),
                batch_updated_at,
                1 if case.get("is_viewed") else 0,
            ),
        )

        conn.commit()


def get_last_update_time(apn: Optional[str] = None) -> Optional[datetime.datetime]:
    with get_db_connection() as conn:
        if apn:
            row = conn.execute(
                "SELECT MAX(updated_at) AS last_update FROM property_cases WHERE apn = ?",
                (apn,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT MAX(updated_at) AS last_update FROM property_cases"
            ).fetchone()

    if not row or not row["last_update"]:
        return None

    try:
        return datetime.datetime.fromisoformat(
            row["last_update"].replace("Z", "+00:00")
        )
    except ValueError:
        return None


def is_data_stale(last_update_dt: Optional[datetime.datetime]) -> bool:
    """Check if the cached data is older than the refresh interval.

    Args:
        last_update_dt: Timestamp of last database update.

    Returns:
        True if data is stale and needs refresh.
    """
    if last_update_dt is None:
        return True

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    age_seconds = (now_utc - last_update_dt).total_seconds()
    return age_seconds >= REFRESH_INTERVAL_SECONDS


def get_all_cases_from_db(apn: Optional[str] = None) -> list[dict]:
    """Retrieve cases from the database, optionally filtered by APN.

    Cases are ordered with open cases first (by priority),
    followed by closed cases.

    Args:
        apn: Optional APN to filter cases by. If None, returns all cases.

    Returns:
        List of case dictionaries.
    """
    with get_db_connection() as conn:
        if apn:
            rows = conn.execute(
                """
                SELECT
                    case_number,
                    case_type,
                    date_closed,
                    last_status,
                    previous_status,
                    priority,
                    complaint_text,
                    detail_url,
                    updated_at,
                    is_viewed
                FROM property_cases
                WHERE apn = ?
                ORDER BY
                    CASE WHEN date_closed IS NULL OR TRIM(date_closed) = '' THEN 0 ELSE 1 END,
                    case_number DESC
                """,
                (apn,)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    case_number,
                    case_type,
                    date_closed,
                    last_status,
                    previous_status,
                    priority,
                    complaint_text,
                    detail_url,
                    updated_at,
                    is_viewed
                FROM property_cases
                ORDER BY
                    CASE WHEN date_closed IS NULL OR TRIM(date_closed) = '' THEN 0 ELSE 1 END,
                    case_number DESC
                """
            ).fetchall()

    cases: list[dict] = []

    for row in rows:
        cases.append(
            {
                "case_number": row["case_number"],
                "case_type": row["case_type"] or "",
                "date_closed": row["date_closed"] or "",
                "last_status": row["last_status"] or "",
                "previous_status": row["previous_status"] or "",
                "priority": row["priority"] or "Unknown",
                "complaint_text": row["complaint_text"] or "",
                "detail_url": row["detail_url"] or "",
                "updated_at": row["updated_at"] or "",
                "is_viewed": bool(row["is_viewed"]),
                "events": [],
            }
        )

    return cases


def get_priority_rank(priority: str) -> int:
    """Get a numeric rank for sorting by priority.

    Args:
        priority: Priority level string.

    Returns:
        Integer rank (lower = higher priority).
    """
    priority_order = {
        "High": 0,
        "Medium": 1,
        "Low": 2,
        "Unknown": 3,
    }
    return priority_order.get(priority, 99)


def build_summary(cases: list[dict]) -> dict:
    """Build a summary of case statistics.

    Args:
        cases: List of all case dictionaries.

    Returns:
        Dictionary containing summary statistics.
    """
    open_cases = [case for case in cases if is_case_active(case)]
    closed_cases = [case for case in cases if not is_case_active(case)]

    # Count only unviewed OPEN cases for notification badge
    actionable_cases = [
        case for case in open_cases if not case.get("is_viewed", False)
    ]

    return {
        "total_cases": len(cases),
        "open_cases": len(open_cases),
        "closed_cases": len(closed_cases),
        "high_priority_cases": sum(
            1 for case in open_cases if case.get("priority") == "High"
        ),
        "unviewed_cases": len(actionable_cases),
    }


def format_last_update(last_update_dt: Optional[datetime.datetime]) -> str:
    """Format a timestamp for display.

    Args:
        last_update_dt: DateTime to format.

    Returns:
        Formatted date string in DD/MM/YYYY HH:MM:SS format.
    """
    if last_update_dt is None:
        return "Never"

    local_dt = last_update_dt.astimezone()
    return local_dt.strftime("%d/%m/%Y %H:%M:%S")


def mark_case_as_viewed(case_number: str, apn: Optional[str] = None) -> bool:
    try:
        with get_db_connection() as conn:
            if apn:
                conn.execute(
                    "UPDATE property_cases SET is_viewed = 1 WHERE case_number = ? AND apn = ?",
                    (case_number, apn),
                )
            else:
                conn.execute(
                    "UPDATE property_cases SET is_viewed = 1 WHERE case_number = ?",
                    (case_number,),
                )
            conn.commit()
        return True
    except sqlite3.Error:
        return False