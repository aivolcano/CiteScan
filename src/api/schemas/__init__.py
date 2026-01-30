"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BibTeXVerifyRequest(BaseModel):
    """Request model for BibTeX verification."""

    bibtex_content: str = Field(
        ...,
        description="BibTeX content to verify",
        min_length=1,
        examples=[
            """@article{example2023,
  title={Example Paper Title},
  author={Smith, John and Doe, Jane},
  journal={Example Journal},
  year={2023}
}"""
        ],
    )


class EntryComparisonResponse(BaseModel):
    """Response model for a single entry comparison."""

    key: str = Field(..., description="BibTeX entry key")
    status: str = Field(..., description="Verification status: verified, warning, or error")
    is_match: bool = Field(..., description="Whether entry matches a database record")
    has_issues: bool = Field(..., description="Whether entry has metadata issues")
    source: Optional[str] = Field(None, description="Data source that verified the entry")
    confidence: float = Field(..., description="Confidence score (0-1)")
    title_match: bool = Field(..., description="Whether title matches")
    author_match: bool = Field(..., description="Whether authors match")
    year_match: bool = Field(..., description="Whether year matches")
    venue_match: Optional[bool] = Field(None, description="Whether venue matches")
    fetched_title: Optional[str] = Field(None, description="Title from database")
    fetched_authors: Optional[list[str]] = Field(None, description="Authors from database")
    fetched_year: Optional[str] = Field(None, description="Year from database")
    fetched_doi: Optional[str] = Field(None, description="DOI from database")
    fetched_url: Optional[str] = Field(None, description="URL from database")
    original_bibtex: str = Field(..., description="Original BibTeX entry")


class DuplicateGroupResponse(BaseModel):
    """Response model for duplicate entry groups."""

    entry_keys: list[str] = Field(..., description="Keys of duplicate entries")
    reason: str = Field(..., description="Reason for duplicate detection")


class BibTeXVerifyResponse(BaseModel):
    """Response model for BibTeX verification."""

    success: bool = Field(..., description="Whether verification completed successfully")
    message: str = Field(..., description="Status message")
    total_count: int = Field(..., description="Total number of entries")
    verified_count: int = Field(..., description="Number of verified entries")
    warning_count: int = Field(..., description="Number of entries with warnings")
    error_count: int = Field(..., description="Number of entries with errors")
    success_rate: float = Field(..., description="Success rate percentage")
    entries: list[EntryComparisonResponse] = Field(..., description="Verification results for each entry")
    duplicate_groups: list[DuplicateGroupResponse] = Field(
        default_factory=list, description="Groups of duplicate entries"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Verification timestamp")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")


class StatsResponse(BaseModel):
    """Response model for statistics."""

    cache_enabled: bool = Field(..., description="Whether cache is enabled")
    cache_size: int = Field(..., description="Current cache size")
    cache_max_size: int = Field(..., description="Maximum cache size")
    cache_ttl: int = Field(..., description="Cache TTL in seconds")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
