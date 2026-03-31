"""
Database models and schema for property case management.

This module contains the Case data model and database schema initialization.
It handles the SQLite3 database structure for storing property complaint cases.
"""

import datetime
import os
import sqlite3
from typing import Optional


class Case:
    """Represents a property complaint case with all associated metadata."""

    def __init__(
        self,
        case_number: str,
        case_type: str = "",
        date_closed: str = "",
        last_status: str = "",
        previous_status: str = "",
        priority: str = "Unknown",
        complaint_text: str = "",
        detail_url: str = "",
        updated_at: str = "",
        is_viewed: bool = False,
        events: Optional[list[dict]] = None,
    ):
        """Initialize a Case instance.

        Args:
            case_number: Unique identifier for the case.
            case_type: Type of complaint (e.g., 'Property Maintenance').
            date_closed: Date when case was closed, if applicable.
            last_status: Most recent status of the case.
            previous_status: Prior status of the case.
            priority: Priority level (High, Medium, Low, Unknown).
            complaint_text: Details of the complaint.
            detail_url: URL to view full case details.
            updated_at: Timestamp of last update.
            is_viewed: Whether the case has been reviewed by a manager.
            events: List of status change events.
        """
        self.case_number = case_number
        self.case_type = case_type
        self.date_closed = date_closed
        self.last_status = last_status
        self.previous_status = previous_status
        self.priority = priority
        self.complaint_text = complaint_text
        self.detail_url = detail_url
        self.updated_at = updated_at
        self.is_viewed = is_viewed
        self.events = events or []

    def to_dict(self) -> dict:
        """Convert Case to dictionary representation.

        Returns:
            Dictionary containing all case attributes.
        """
        return {
            "case_number": self.case_number,
            "case_type": self.case_type,
            "date_closed": self.date_closed,
            "last_status": self.last_status,
            "previous_status": self.previous_status,
            "priority": self.priority,
            "complaint_text": self.complaint_text,
            "detail_url": self.detail_url,
            "updated_at": self.updated_at,
            "is_viewed": self.is_viewed,
            "events": self.events,
        }

    @staticmethod
    def from_dict(data: dict) -> "Case":
        """Create a Case instance from dictionary.

        Args:
            data: Dictionary containing case attributes.

        Returns:
            Case instance.
        """
        return Case(
            case_number=data.get("case_number", ""),
            case_type=data.get("case_type", ""),
            date_closed=data.get("date_closed", ""),
            last_status=data.get("last_status", ""),
            previous_status=data.get("previous_status", ""),
            priority=data.get("priority", "Unknown"),
            complaint_text=data.get("complaint_text", ""),
            detail_url=data.get("detail_url", ""),
            updated_at=data.get("updated_at", ""),
            is_viewed=data.get("is_viewed", False),
            events=data.get("events", []),
        )


def get_db_path() -> str:
    """Get the database file path.

    Returns:
        Absolute path to the cases.db file.
    """
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "cases.db")


def get_db_connection() -> sqlite3.Connection:
    """Create and return a database connection.

    Returns:
        SQLite3 connection with row factory configured.
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column_exists(
    conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str
) -> None:
    """Ensure a column exists in the database table, adding it if necessary.

    Args:
        conn: Database connection.
        table_name: Name of the table to check.
        column_name: Name of the column to ensure exists.
        column_sql: SQL definition for the column (e.g., 'INTEGER DEFAULT 0').
    """
    existing_columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }

    if column_name not in existing_columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def init_db() -> None:
    """Initialize the database with the required schema.

    Creates the property_cases table if it doesn't exist and ensures
    backward compatibility with older database structures.
    """
    with get_db_connection() as conn:
        conn.execute(
        """
        CREATE TABLE IF NOT EXISTS property_cases (
            case_number TEXT,
            case_type TEXT,
            apn TEXT,
            date_closed TEXT,
            last_status TEXT,
            previous_status TEXT,
            priority TEXT,
            complaint_text TEXT,
            detail_url TEXT,
            updated_at TEXT,
            is_viewed INTEGER DEFAULT 0,
            PRIMARY KEY (apn, case_number, case_type)
        )
        """
        )

        # Support for old DB files - add missing columns if they don't exist
        ensure_column_exists(conn, "property_cases", "apn", "apn TEXT")
        ensure_column_exists(conn, "property_cases", "previous_status", "previous_status TEXT")
        ensure_column_exists(conn, "property_cases", "is_viewed", "is_viewed INTEGER DEFAULT 0")

        conn.commit()
