class ReportError(Exception):
    """Base exception for report-related errors."""

    pass


class AnalysisNotFoundError(ReportError):
    """Custom exception raised when a video analysis is not found for a user."""

    pass


class AnalysisNotCompletedError(ReportError):
    """Custom exception raised when a video analysis is not completed."""

    pass
