"""Health check and system routes."""
from fastapi import APIRouter

from src.api.schemas import HealthResponse, StatsResponse
from src.api.dependencies import CacheManagerDep
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the service is running and healthy",
)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Health status
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get statistics",
    description="Get system statistics including cache information",
)
async def get_stats(cache: CacheManagerDep) -> StatsResponse:
    """Get system statistics.

    Args:
        cache: Cache manager instance

    Returns:
        System statistics
    """
    cache_stats = cache.get_stats()

    return StatsResponse(
        cache_enabled=cache_stats["enabled"],
        cache_size=cache_stats["size"],
        cache_max_size=cache_stats["max_size"],
        cache_ttl=cache_stats["ttl"],
    )
