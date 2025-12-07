class ReportError(Exception):
    """Base exception for report-related errors."""

    pass


class AnalysisNotCompletedError(ReportError):
    """Custom exception raised when a video analysis is not completed."""

    pass
