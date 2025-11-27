class PatientServiceError(Exception):
    """Base exception for patient service errors."""

    ...


class PatientServiceUnavailableError(PatientServiceError):
    """Raised when the patient service cannot be reached (network/timeout errors)."""

    ...


class PatientServiceResponseError(PatientServiceError):
    """Raised when the patient service returns an invalid or unexpected response."""

    ...
