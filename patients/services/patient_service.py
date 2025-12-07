import logging

from larvixon_site.settings import (
    MOCK_PATIENT_SERVICE,
    PATIENT_SERVICE_URL,
)

from patients.services.api_patient_service import APIPatientService
from patients.services.base_patient_service import BasePatientService
from patients.services.mock_patient_service import MockPatientService

logger: logging.Logger = logging.getLogger(__name__)

PESEL_ID = "http://hl7.org/fhir/sid/pesel"
TIMEOUT_SECONDS = 90
CACHE_TIME_SECONDS = 60


def get_patient_service() -> BasePatientService:
    if MOCK_PATIENT_SERVICE:
        return MockPatientService()
    return APIPatientService(PATIENT_SERVICE_URL)


patient_service: BasePatientService = get_patient_service()
