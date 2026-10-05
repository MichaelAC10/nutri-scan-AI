"""
Custom exceptions for NutriScan AI.

Keeping these in one place lets every other module raise/catch
specific, meaningful errors instead of generic Exceptions.
"""


class NutriScanError(Exception):
    """Base class for all app-specific errors."""
    pass


class InvalidBarcodeError(NutriScanError):
    """Raised when a barcode fails format validation (regex check)."""
    pass


class ProductNotFoundError(NutriScanError):
    """Raised when Open Food Facts has no record for the query/barcode."""
    pass


class APIRequestError(NutriScanError):
    """Raised when a network/API call fails (timeout, connection, bad status)."""
    pass


class IncompleteDataError(NutriScanError):
    """Raised when a product exists but lacks the nutrition fields we need."""
    pass


class SuggestionGenerationError(NutriScanError):
    """Raised when the Gemini API call for explanations/suggestions fails."""
    pass


class FoodLogError(NutriScanError):
    """Raised for file I/O problems when reading/writing the food log."""
    pass
