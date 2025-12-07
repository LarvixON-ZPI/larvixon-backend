from uuid import UUID
from abc import ABC, abstractmethod
from typing import List
import logging

from patients.errors import (
    PatientInvalidUUIDError,
)

logger: logging.Logger = logging.getLogger(__name__)


class BasePatientService(ABC):
    @abstractmethod
    def search_patients(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        pesel: str | None = None,
    ) -> List[dict]:
        """Search for patients by first name, last name, or PESEL."""
        pass

    @abstractmethod
    def get_patient_by_guid(self, guid: str) -> dict | None:
        """Get a single patient by their GUID."""
        pass

    @abstractmethod
    def get_patients_by_guids(self, guids: List[str]) -> dict[str, dict]:
        """Get multiple patients by their GUIDs."""
        pass

    def validate_uuid(self, guid: str) -> None:
        """Validate that the provided GUID is a valid UUID."""
        try:
            UUID(guid)
        except ValueError:
            logger.warning(f"Invalid Patient GUID format provided: {guid}")
            raise PatientInvalidUUIDError(f"Invalid Patient GUID format: {guid}")
