"""Custom exceptions for CiteScan."""


class CiteScanException(Exception):
    """Base exception for CiteScan."""

    def __init__(self, message: str, details: dict | None = None):
        """Initialize exception.

        Args:
            message: Error message
            details: Optional additional details
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class FetcherException(CiteScanException):
    """Exception raised by fetchers."""

    def __init__(self, message: str, source: str, details: dict | None = None):
        """Initialize fetcher exception.

        Args:
            message: Error message
            source: Fetcher source (e.g., 'arxiv', 'crossref')
            details: Optional additional details
        """
        self.source = source
        super().__init__(message, details)


class ParserException(CiteScanException):
    """Exception raised by parsers."""

    pass


class ValidationException(CiteScanException):
    """Exception raised during validation."""

    pass


class RateLimitException(FetcherException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, source: str, retry_after: int | None = None):
        """Initialize rate limit exception.

        Args:
            source: Fetcher source
            retry_after: Seconds to wait before retry
        """
        self.retry_after = retry_after
        message = f"Rate limit exceeded for {source}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, source)


class TimeoutException(FetcherException):
    """Exception raised when request times out."""

    def __init__(self, source: str, timeout: int):
        """Initialize timeout exception.

        Args:
            source: Fetcher source
            timeout: Timeout value in seconds
        """
        message = f"Request to {source} timed out after {timeout} seconds"
        super().__init__(message, source)
