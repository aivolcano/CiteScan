"""Verification API routes."""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from src.api.schemas import (
    BibTeXVerifyRequest,
    BibTeXVerifyResponse,
    EntryComparisonResponse,
    DuplicateGroupResponse,
    ErrorResponse,
)
from src.api.dependencies import VerificationServiceDep
from src.core.logging import get_logger
from src.core.exceptions import ParserException, FetcherException

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["verification"])


def _get_entry_status(comparison) -> str:
    """Determine entry status from comparison result."""
    if comparison and comparison.is_match:
        return "verified"
    elif comparison and comparison.has_issues:
        return "warning"
    return "error"


@router.post(
    "/verify",
    response_model=BibTeXVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify BibTeX entries",
    description="Verify BibTeX entries against multiple academic databases",
    responses={
        200: {"description": "Verification completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid BibTeX content"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def verify_bibtex(
    request: BibTeXVerifyRequest,
    service: VerificationServiceDep,
) -> BibTeXVerifyResponse:
    """Verify BibTeX entries.

    Args:
        request: BibTeX verification request
        service: Verification service instance

    Returns:
        Verification results

    Raises:
        HTTPException: If verification fails
    """
    try:
        logger.info("Received BibTeX verification request")

        # Verify BibTeX
        result = service.verify_bibtex_string(request.bibtex_content)

        # Convert entry reports to response format
        entries = []
        for entry_report in result.entry_reports:
            entry = entry_report.entry
            comparison = entry_report.comparison

            # Format original BibTeX
            bibtex_str = f"@{entry.entry_type}{{{entry.key},\n"
            for field, value in (entry.raw_entry or {}).items():
                if field in ("ID", "ENTRYTYPE"):
                    continue
                if value is not None and str(value).strip():
                    bibtex_str += f"  {field}={{{value}}},\n"
            bibtex_str = bibtex_str.rstrip(",\n") + "\n}"

            entry_response = EntryComparisonResponse(
                key=entry.key,
                status=_get_entry_status(comparison),
                is_match=comparison.is_match if comparison else False,
                has_issues=comparison.has_issues if comparison else False,
                source=getattr(comparison, "source", None) if comparison else None,
                confidence=getattr(comparison, "confidence", 0.0) if comparison else 0.0,
                title_match=comparison.title_match if comparison else False,
                author_match=comparison.author_match if comparison else False,
                year_match=comparison.year_match if comparison else False,
                venue_match=getattr(comparison, "venue_match", None) if comparison else None,
                fetched_title=getattr(comparison, "fetched_title", None) if comparison else None,
                fetched_authors=getattr(comparison, "fetched_authors", None) if comparison else None,
                fetched_year=getattr(comparison, "fetched_year", None) if comparison else None,
                fetched_doi=getattr(comparison, "fetched_doi", None) if comparison else None,
                fetched_url=getattr(comparison, "fetched_url", None) if comparison else None,
                original_bibtex=bibtex_str,
            )
            entries.append(entry_response)

        # Convert duplicate groups
        duplicate_groups = [
            DuplicateGroupResponse(
                entry_keys=group.entry_keys,
                reason=group.reason,
            )
            for group in result.duplicate_groups
        ]

        response = BibTeXVerifyResponse(
            success=True,
            message="Verification completed successfully",
            total_count=result.total_count,
            verified_count=result.verified_count,
            warning_count=result.warning_count,
            error_count=result.error_count,
            success_rate=result.success_rate,
            entries=entries,
            duplicate_groups=duplicate_groups,
        )

        logger.info(
            f"Verification completed: {result.verified_count}/{result.total_count} verified"
        )
        return response

    except ParserException as e:
        logger.error(f"Parser error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "ParserError", "message": str(e)},
        )

    except FetcherException as e:
        logger.error(f"Fetcher error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "FetcherError", "message": str(e)},
        )

    except Exception as e:
        logger.exception(f"Unexpected error during verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "InternalError", "message": "An unexpected error occurred"},
        )
