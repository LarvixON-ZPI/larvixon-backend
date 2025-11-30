import requests
from abc import ABC, abstractmethod
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
TIMEOUT_SECONDS = 90
CACHE_TIME_SECONDS = 60


class BasePatientService(ABC):
    @abstractmethod
    def search_patients(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        pesel: Optional[str] = None,
    ) -> List[dict]:
        """Search for patients by first name, last name, or PESEL."""
        pass

    @abstractmethod
    def get_patient_by_guid(self, guid: str) -> Optional[dict]:
        """Get a single patient by their GUID."""
        pass

    @abstractmethod
    def get_patients_by_guids(self, guids: List[str]) -> dict[str, dict]:
        """Get multiple patients by their GUIDs."""
        pass


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
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        pesel: Optional[str] = None,
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

    def get_patient_by_guid(self, guid: str) -> Optional[dict]:
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


class APIPatientService(BasePatientService):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def search_patients(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        pesel: Optional[str] = None,
    ) -> List[dict]:
        cache_key = f"patient_search:first_name={first_name or ''}:last_name={last_name or ''}:pesel={pesel or ''}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            url: str = f"{self.base_url}/api/patients"
            params = {}
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name
            if pesel:
                params["pesel"] = pesel

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

    def get_patients_by_guids(self, guids: List[str]) -> dict[str, dict]:
        if not guids:
            return {}

        results = {}
        cache_keys = {guid: f"patient:{guid}" for guid in guids}
        cached_patients = cache.get_many(cache_keys.values())

        uncached_guids = []
        for guid, cache_key in cache_keys.items():
            cached = cached_patients.get(cache_key)
            if cached is not None:
                results[guid] = cached
            else:
                uncached_guids.append(guid)

        if not uncached_guids:
            return results

        try:
            url: str = f"{self.base_url}/api/patients/search-by-guids"
            payload = {"guids": uncached_guids}

            response: requests.Response = requests.post(
                url, json=payload, timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()

            data = response.json()
            entries: list = data.get("entry", [])

            cache_batch = {}
            for entry in entries:
                resource: dict = entry.get("resource", {})
                patient = self._parse_fhir_patient(resource)
                patient_guid = patient.get("id")

                if patient_guid:
                    results[str(patient_guid)] = patient
                    cache_key = f"patient:{patient_guid}"
                    cache_batch[cache_key] = patient

            if cache_batch:
                cache.set_many(cache_batch, CACHE_TIME_SECONDS)

            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Patient Service: {e}")
            raise PatientServiceUnavailableError(
                f"Patient service unavailable: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error in get_patients_by_guids: {e}")
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

        internal_guid = fhir_resource.get("id")

        return {
            "id": internal_guid,
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


def get_patient_service() -> BasePatientService:
    if MOCK_PATIENT_SERVICE:
        return MockPatientService()
    return APIPatientService(PATIENT_SERVICE_URL)


patient_service: BasePatientService = get_patient_service()
