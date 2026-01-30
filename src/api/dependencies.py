"""API dependencies and dependency injection."""
from typing import Annotated
from fastapi import Depends

from src.services import VerificationService
from src.core.cache import cache_manager


def get_verification_service() -> VerificationService:
    """Get verification service instance.

    Returns:
        VerificationService instance
    """
    return VerificationService()


def get_cache_manager():
    """Get cache manager instance.

    Returns:
        CacheManager instance
    """
    return cache_manager


# Type aliases for dependency injection
VerificationServiceDep = Annotated[VerificationService, Depends(get_verification_service)]
CacheManagerDep = Annotated[type(cache_manager), Depends(get_cache_manager)]
