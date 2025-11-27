import requests
from typing import Optional, List
import logging
from django.core.cache import cache

from larvixon_site.settings import MOCK_PATIENT_SERVICE, PATIENT_SERVICE_URL
from patients.errors import (
    PatientServiceUnavailableError,
    PatientServiceResponseError,
)

logger: logging.Logger = logging.getLogger(__name__)

PESEL_ID = "http://hl7.org/fhir/sid/pesel"
TIMEOUT_SECONDS = 5
CACHE_TIME_SECONDS = 60


class PatientService:
    def __init__(self) -> None:
        self.base_url: str = PATIENT_SERVICE_URL
        self.mock_mode: bool = MOCK_PATIENT_SERVICE

    def search_patients(self, search_term: Optional[str] = None) -> List[dict]:
        if self.mock_mode:
            return self._mock_search_patients(search_term)

        cache_key = f"patient_search:{search_term or ''}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            url: str = f"{self.base_url}/api/patients"
            params = {}
            if search_term:
                params["search"] = search_term

            response: requests.Response = requests.get(
                url, params=params, timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()

            data = response.json()

            entries: list = data.get("entry", [])
            patients: list = []
            for entry in entries:
                resource: dict = entry.get("resource", {})
                patients.append(self._parse_fhir_patient(resource))

            cache.set(cache_key, patients, CACHE_TIME_SECONDS)

            return patients

        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Patient Service: {e}")
            raise PatientServiceUnavailableError(
                f"Patient service unavailable: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error in search_patients: {e}")
            raise PatientServiceResponseError(
                f"Unexpected error in patient service: {e}"
            ) from e

    def get_patient_by_guid(self, guid: str) -> Optional[dict]:
        if self.mock_mode:
            return self._mock_get_patient(guid)

        cache_key = f"patient:{guid}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            url: str = f"{self.base_url}/api/patients/{guid}"
            response: requests.Response = requests.get(url, timeout=TIMEOUT_SECONDS)
            if response.status_code == 404:
                return None
            response.raise_for_status()

            data = response.json()
            patient = self._parse_fhir_patient(data)

            cache.set(cache_key, patient, CACHE_TIME_SECONDS)

            return patient
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Patient Service: {e}")
            raise PatientServiceUnavailableError(
                f"Patient service unavailable: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error in get_patient_by_guid: {e}")
            raise PatientServiceResponseError(
                f"Unexpected error processing patient data: {e}"
            ) from e

    def _parse_fhir_patient(self, fhir_resource: dict) -> dict:
        pesel = None
        identifiers = fhir_resource.get("identifier", [])
        for identifier in identifiers:
            if identifier.get("system") == PESEL_ID:
                pesel = identifier.get("value")
                break

        first_name = ""
        last_name = ""
        names = fhir_resource.get("name", [])
        if names:
            name = names[0]
            last_name = name.get("family", "")
            given = name.get("given", [])
            if given:
                first_name = given[0]

        birth_date = fhir_resource.get("birthDate")
        gender = fhir_resource.get("gender")

        phone = None
        email = None
        telecoms = fhir_resource.get("telecom", [])
        for telecom in telecoms:
            if telecom.get("system") == "phone":
                phone = telecom.get("value")
            elif telecom.get("system") == "email":
                email = telecom.get("value")

        address_line = None
        city = None
        postal_code = None
        country = None
        addresses = fhir_resource.get("address", [])
        if addresses:
            address = addresses[0]
            lines = address.get("line", [])
            if lines:
                address_line = lines[0]
            city = address.get("city")
            postal_code = address.get("postalCode")
            country = address.get("country")

        # todo: We need to get internal_guid from somewhere
        # For now, use the FHIR id field
        fhir_id = fhir_resource.get("id", "")
        if fhir_id.startswith("patient-"):
            internal_guid = fhir_id[len("patient-") :]
        else:
            internal_guid = fhir_id

        return {
            "internal_guid": internal_guid,
            "pesel": pesel,
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": birth_date,
            "gender": gender,
            "phone": phone,
            "email": email,
            "address_line": address_line,
            "city": city,
            "postal_code": postal_code,
            "country": country,
        }

    def _mock_search_patients(self, search_term: Optional[str] = None) -> List[dict]:
        mock_patient = self._get_mock_patient()

        if search_term:
            search_lower = search_term.lower()
            if (
                search_lower in mock_patient["first_name"].lower()
                or search_lower in mock_patient["last_name"].lower()
                or (mock_patient["pesel"] and search_lower in mock_patient["pesel"])
            ):
                return [mock_patient]
            return []

        return [mock_patient]

    def _mock_get_patient(self, guid: str) -> Optional[dict]:
        mock_patient = self._get_mock_patient()
        if mock_patient["internal_guid"] == guid:
            return mock_patient
        return None

    def _get_mock_patient(self) -> dict:
        return {
            "internal_guid": "00000000-0000-0000-0000-000000000001",
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


patient_service = PatientService()
