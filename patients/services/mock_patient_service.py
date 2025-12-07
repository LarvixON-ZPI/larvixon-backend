from typing import List
import logging

from patients.services.base_patient_service import BasePatientService

logger: logging.Logger = logging.getLogger(__name__)

PESEL_ID = "http://hl7.org/fhir/sid/pesel"
TIMEOUT_SECONDS = 90
CACHE_TIME_SECONDS = 60


class MockPatientService(BasePatientService):
    def _get_mock_patient(self) -> dict:
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "pesel": "90010112345",
            "first_name": "Jan",
            "last_name": "Kowalski",
            "birth_date": "1990-01-01",
            "gender": "male",
            "phone": "+48123456789",
            "email": "jan.kowalski@example.com",
            "address_line": "ul. Przykładowa 1",
            "city": "Warszawa",
            "postal_code": "00-001",
            "country": "PL",
        }

    def search_patients(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        pesel: str | None = None,
    ) -> List[dict]:
        mock_patient = self._get_mock_patient()

        if first_name or last_name or pesel:
            if (
                first_name
                and first_name.lower() in mock_patient["first_name"].lower()
                or last_name
                and last_name.lower() in mock_patient["last_name"].lower()
                or pesel
                and pesel in mock_patient["pesel"]
            ):
                return [mock_patient]
            return []

        return [mock_patient]

    def get_patient_by_guid(self, guid: str) -> dict | None:
        mock_patient = self._get_mock_patient()
        if mock_patient["id"] == guid:
            return mock_patient
        return None

    def get_patients_by_guids(self, guids: List[str]) -> dict[str, dict]:
        mock_patient = self._get_mock_patient()
        results = {}

        for guid in guids:
            if mock_patient["id"] == guid:
                results[guid] = mock_patient

        return results
