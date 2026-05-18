"""Project-specific exceptions used to distinguish hard failures from degraded fallbacks."""

class ReferralSystemError(Exception):
    """Base exception for the referral intelligence platform."""


class UnsupportedFileTypeError(ReferralSystemError):
    """Raised when an uploaded file type is not supported."""


class CorruptedDocumentError(ReferralSystemError):
    """Raised when a document cannot be parsed or is structurally invalid."""


class OCRProcessingError(ReferralSystemError):
    """Raised when OCR extraction fails."""


class LLMServiceError(ReferralSystemError):
    """Raised when the LLM layer fails after retries."""


class ArchiveExtractionError(ReferralSystemError):
    """Raised when an archive cannot be safely extracted."""
