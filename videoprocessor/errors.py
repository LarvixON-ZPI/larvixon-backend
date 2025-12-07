class VideoProcessingError(Exception):
    """Base exception for video processing errors."""

    pass


class VideoForUploadTooLargeError(VideoProcessingError):
    """Raised when the video file for upload exceeds the maximum allowed size."""

    def __init__(self, file_size: int, max_size: int):
        self.file_size = file_size
        self.max_size = max_size
        super().__init__(
            f"Video file size {file_size} exceeds maximum allowed size of {max_size}."
        )


class VideoNoUploadIDError(VideoProcessingError):
    """Raised when no upload ID is provided for chunked upload."""

    def __init__(self, message: str = "No upload ID provided for chunked upload"):
        self.message = message
        super().__init__(self.message)


class VideoNoFilenameError(VideoProcessingError):
    """Raised when no filename is provided for chunked upload."""

    def __init__(self, message: str = "No filename provided for chunked upload"):
        self.message = message
        super().__init__(self.message)


class VideoNoFileError(VideoProcessingError):
    """Raised when no video file is provided."""

    def __init__(self, message: str = "No video file provided"):
        self.message = message
        super().__init__(self.message)


class VideoWrongFormatError(VideoProcessingError):
    """Raised when the video file format is not supported."""

    def __init__(self, message: str = "Unsupported video file format"):
        self.message = message
        super().__init__(self.message)


class VideoAnalysisNotFoundError(VideoProcessingError):
    """Raised when a video analysis record is not found."""

    def __init__(self, analysis_id: int):
        self.analysis_id = analysis_id
        super().__init__(f"VideoAnalysis with ID {analysis_id} not found.")


class MLPredictionError(VideoProcessingError):
    """Raised when ML model prediction fails."""

    def __init__(self, message: str = "ML model prediction failed"):
        self.message = message
        super().__init__(self.message)


class VideoFileAccessError(VideoProcessingError):
    """Raised when there's an error accessing the video file."""

    def __init__(self, message: str = "Failed to access video file"):
        self.message = message
        super().__init__(self.message)
