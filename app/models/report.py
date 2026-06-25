"""
SentinelOps — Report Data Models
====================================
Pydantic schemas for report generation requests and responses.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ReportFormat(str, Enum):
    """Supported report output formats."""

    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ReportRequest(BaseModel):
    """Request body for generating a report."""

    format: ReportFormat = Field(..., description="Output format.")
    date_from: datetime | None = Field(
        default=None, description="Start of date range (ISO 8601)."
    )
    date_to: datetime | None = Field(
        default=None, description="End of date range (ISO 8601)."
    )
    include_charts: bool = Field(
        default=True, description="Embed charts in Excel/PDF reports."
    )
    include_screenshots: bool = Field(
        default=True, description="Embed alert screenshots in PDF reports."
    )
    title: str = Field(
        default="SentinelOps Violation Report",
        description="Report title (used in PDF header).",
    )


class ReportMetadata(BaseModel):
    """Metadata returned after a report is generated."""

    report_id: str = Field(..., description="Unique report identifier.")
    format: ReportFormat = Field(..., description="Report output format.")
    filename: str = Field(..., description="Generated filename.")
    generated_at: datetime = Field(..., description="Generation timestamp (UTC).")
    file_path: str = Field(..., description="Relative path to the report file.")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes.")
