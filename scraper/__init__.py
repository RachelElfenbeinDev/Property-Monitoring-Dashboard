"""
Scraper package for fetching and parsing property complaint cases.

Submodules:
- engine: HTTP request handling and HTML fetching
- parsers: HTML parsing and data extraction
- transformer: Case enrichment and priority calculation
"""

# Export main functions for convenience
from scraper.engine import (
    extract_cases_from_main_page,
    fetch_case_detail,
    load_property_cases_page,
    validate_apn,
)
from scraper.parsers import extract_complaint_text_from_soup, extract_case_timeline_from_soup
from scraper.transformer import enrich_case, calculate_priority

__all__ = [
    "validate_apn",
    "load_property_cases_page",
    "extract_cases_from_main_page",
    "fetch_case_detail",
    "extract_complaint_text_from_soup",
    "extract_case_timeline_from_soup",
    "enrich_case",
    "calculate_priority",
]
