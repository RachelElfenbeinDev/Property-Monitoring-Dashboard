"""
Flask routes and API endpoints.

This module defines all HTTP routes and API endpoints for the application.
"""

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Tuple

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.models import init_db
from app.services import (
    annotate_changes,
    build_summary,
    format_last_update,
    get_all_cases_from_db,
    get_last_update_time,
    get_priority_rank,
    is_case_active,
    is_data_stale,
    mark_case_as_viewed,
    save_cases,
)
from scraper.engine import (
    extract_cases_from_main_page,
    fetch_case_detail,
    load_property_cases_page,
    validate_apn,
)
from scraper.transformer import enrich_case

main_bp = Blueprint("main", __name__)

MAX_WORKERS = 8


def fetch_and_save_cases(apn: str) -> list[dict]:
    """Fetch and save cases from the property database.

    Loads the main cases page, extracts case listings, fetches details
    for each case, and saves them to the database.

    Args:
        apn: The 10-digit Assessor Parcel Number.

    Returns:
        List of enriched case dictionaries.

    Raises:
        ValueError: If APN format is invalid.
    """
    if not validate_apn(apn):
        raise ValueError(f"Invalid APN format: {apn}. APN must be exactly 10 digits.")

    main_html = load_property_cases_page(apn)
    cases = extract_cases_from_main_page(main_html)

    enrich = partial(
        enrich_case,
        fetch_func=lambda case_no: fetch_case_detail(case_no, apn),
        is_active_func=is_case_active,
    )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        cases = list(executor.map(enrich, cases))

    annotate_changes(cases,apn)
    save_cases(cases, apn)

    return cases


@main_bp.route("/")
def home() -> str:
    """Home page - show search form for APN entry.

    Returns:
        Rendered search page.
    """
    init_db()
    
    # Clear any previously stored APN to force fresh search
    session.pop("apn", None)
    
    # Always show search page by default
    return render_template("search.html")


def _render_dashboard(apn: str) -> str:
    """Helper function to render the dashboard for a given APN.

    Args:
        apn: The 10-digit Assessor Parcel Number.

    Returns:
        Rendered dashboard page.
    """
    error_message = None
    last_update = get_last_update_time(apn)

    if is_data_stale(last_update):
        try:
            cases = fetch_and_save_cases(apn)
            last_update = get_last_update_time(apn)
        except Exception as exc:
            cases = get_all_cases_from_db(apn)
            error_message = (
                f"Could not refresh live data. Showing last saved snapshot. ({exc})"
            )
    else:
        cases = get_all_cases_from_db(apn)

    open_cases = sorted(
        [case for case in cases if is_case_active(case)],
        key=lambda case: (
            get_priority_rank(case.get("priority", "Unknown")),
            case.get("case_number", ""),
        ),
    )

    closed_cases = sorted(
        [case for case in cases if not is_case_active(case)],
        key=lambda case: (
            get_priority_rank(case.get("priority", "Unknown")),
            case.get("case_number", ""),
        ),
    )

    summary = build_summary(cases)

    return render_template(
        "dashboard.html",
        open_cases=open_cases,
        closed_cases=closed_cases,
        summary=summary,
        last_update_display=format_last_update(last_update),
        error_message=error_message,
        current_apn=apn,
    )


@main_bp.route("/refresh", methods=["POST"])
def refresh_data() -> str:
    """Refresh case data for the current APN.

    Returns:
        Redirect to dashboard page.
    """
    apn = session.get("apn")
    if apn:
        fetch_and_save_cases(apn)
    return redirect(url_for("main.view_dashboard"))


@main_bp.route("/dashboard")
def view_dashboard() -> str:
    """Dashboard page - display cases for the current APN.

    Returns:
        Rendered dashboard page.
    """
    init_db()

    # Check if APN is set in session
    apn = session.get("apn")

    if not apn:
        # No APN set, redirect to search
        return redirect(url_for("main.home"))

    return _render_dashboard(apn)


@main_bp.route("/api/search", methods=["POST"])
def api_search() -> Tuple[dict, int]:
    """API endpoint to search for cases by APN.

    Validates the APN, fetches and saves cases, and returns success response.

    Request JSON:
        apn (str): The 10-digit APN to search.

    Returns:
        JSON response with success status and redirect URL, or error message.
    """
    data = request.get_json()
    apn = (data.get("apn") or "").strip() if data else ""

    if not apn:
        return jsonify({"error": "APN is required"}), 400

    if not validate_apn(apn):
        return (
            jsonify({"error": "Invalid APN format. Must be exactly 10 digits."}),
            400,
        )

    try:
        session["apn"] = apn
        cases = fetch_and_save_cases(apn)
        return jsonify(
            {"success": True, "cases_count": len(cases), "redirect": url_for("main.view_dashboard")}
        ), 200
    except Exception as exc:
        return jsonify({"error": f"Failed to fetch cases: {str(exc)}"}), 500


@main_bp.route("/clear_apn", methods=["POST"])
def clear_apn() -> str:
    """Clear the current APN and return to search.

    Returns:
        Redirect to home page.
    """
    session.pop("apn", None)
    return redirect(url_for("main.home"))


@main_bp.route("/api/mark_case_viewed", methods=["POST"])
def api_mark_case_viewed() -> Tuple[dict, int]:
    """API endpoint to mark a case as viewed.

    Request JSON:
        case_number (str): The case number to mark as viewed.

    Returns:
        JSON response with updated unviewed count or error message.
    """
    data = request.get_json()
    case_number = (data.get("case_number") or "").strip() if data else ""

    if not case_number:
        return jsonify({"error": "case_number is required"}), 400
    
    apn = session.get("apn")
    if not apn:
        return jsonify({"error": "No APN in session"}), 400

    try:
        if mark_case_as_viewed(case_number,apn):
            # Get updated summary
            cases = get_all_cases_from_db(apn)
            summary = build_summary(cases)

            return jsonify(
                {"success": True, "unviewed_count": summary["unviewed_cases"]}
            ), 200
        else:
            return jsonify({"error": "Failed to update case"}), 500
    except Exception as exc:
        return jsonify({"error": f"Failed to update case: {str(exc)}"}), 500


@main_bp.route("/api/case_detail/<case_number>", methods=["GET"])
def api_case_detail(case_number: str) -> Tuple[dict, int]:
    """Get detailed information about a specific case.

    Args:
        case_number: The case number to retrieve details for.

    Returns:
        JSON response with case details or error message.
    """
    case_number = case_number.strip()

    apn = session.get("apn")
    if not apn:
        return jsonify({"error": "No APN in session"}), 400

    try:
        cases = get_all_cases_from_db(apn)
        case = next(
            (c for c in cases if c["case_number"] == case_number), None
        )

        if not case:
            return jsonify({"error": "Case not found"}), 404

        return jsonify({"success": True, "case": case}), 200
    except Exception as exc:
        return jsonify({"error": f"Failed to retrieve case: {str(exc)}"}), 500


@main_bp.route("/api/actionable_cases", methods=["GET"])
def api_actionable_cases() -> Tuple[dict, int]:
    """Get list of actionable (unreviewed, open) cases for notifications.

    Returns:
        JSON response with list of actionable cases.
    """
    try:
        apn = session.get("apn")
        if not apn:
            return jsonify({"error": "No APN in session"}), 400
        cases = get_all_cases_from_db(apn)
        open_cases = [case for case in cases if is_case_active(case)]
        actionable_cases = [
            case for case in open_cases if not case.get("is_viewed", False)
        ]

        # Sort by priority
        actionable_cases.sort(
            key=lambda c: get_priority_rank(c.get("priority", "Unknown"))
        )

        return jsonify({"success": True, "actionable_cases": actionable_cases}), 200
    except Exception as exc:
        return jsonify({"error": f"Failed to retrieve cases: {str(exc)}"}), 500
