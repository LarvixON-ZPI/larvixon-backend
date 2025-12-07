class AnalysisError(Exception):
    """Base class for analysis-related errors."""

    pass


class AnalysisNotFoundError(AnalysisError):
    """Raised when an analysis is not found."""

    pass


class AnalysisCannotBeRetriedError(AnalysisError):
    """Raised when an analysis cannot be retried."""

    def __init__(
        self,
        message: str = "This analysis cannot be retried.",
    ):
        self.message = message
        super().__init__(self.message)


class AnalysisNotFailedError(AnalysisCannotBeRetriedError):
    """Raised when attempting to retry an analysis that is not in FAILED status."""

    def __init__(self):
        super().__init__("Only failed analyses can be retried.")


class AnalysisTooOldError(AnalysisCannotBeRetriedError):
    """Raised when an analysis is too old to retry."""

    def __init__(self, video_lifetime_days: int):
        super().__init__(
            f"Analysis is too old to retry. Only analyses created within the last {video_lifetime_days} days can be retried."
        )


class AnalysisVideoNotFoundError(AnalysisCannotBeRetriedError):
    """Raised when the video file for an analysis no longer exists."""

    def __init__(self):
        super().__init__("Video file no longer exists. Cannot retry this analysis.")
