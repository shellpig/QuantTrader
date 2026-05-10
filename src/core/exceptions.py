"""Domain-specific exceptions."""


class DataQualityError(Exception):
    """Raised when data quality checks fail."""


class FetcherError(Exception):
    """Raised when a data fetch operation fails."""


class StorageError(Exception):
    """Raised when storage read/write operations fail."""


class AIDisabledError(Exception):
    """Raised when AI functionality is disabled by configuration."""


class AICallError(Exception):
    """Raised when an AI provider call fails or returns invalid payload."""
