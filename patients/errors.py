class PatientServiceError(Exception):
    """Base exception for patient service errors."""

    ...


class PatientServiceUnavailableError(PatientServiceError):
    """Raised when the patient service cannot be reached (network/timeout errors)."""

    ...


class PatientServiceResponseError(PatientServiceError):
    """Raised when the patient service returns an invalid or unexpected response."""

    ...


class PatientInvalidUUIDError(PatientServiceError):
    """Raised when the provided Patient GUID is not a valid UUID."""

    ...


class PatientNotFoundError(PatientServiceError):
    """Raised when a patient with the specified GUID is not found."""

    ...
