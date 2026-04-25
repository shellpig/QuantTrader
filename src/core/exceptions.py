"""Domain-specific exceptions."""


class DataQualityError(Exception):
    """Raised when data quality checks fail."""


class FetcherError(Exception):
    """Raised when a data fetch operation fails."""


class StorageError(Exception):
    """Raised when storage read/write operations fail."""
