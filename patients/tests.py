import sys
from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.request import Request
from rest_framework.response import Response
import requests

from accounts.models import User
from patients.views.get_patient_view import GetPatientView
from patients.views.search_patients_view import SearchPatientsView
from patients.services import PatientService, patient_service
from patients.errors import (
    PatientServiceUnavailableError,
    PatientServiceResponseError,
)
from larvixon_site.settings import MOCK_PATIENT_SERVICE
from tests.common import TestFixtures, run_tests


class TestPatientViews(TestCase):
    """Test patient API views with authentication and edge cases."""

    # Mock FHIR data fixtures
    MOCK_PATIENT_SINGLE = {
        "resourceType": "Patient",
        "internal_guid": "ab758f9b-0298-4823-b144-ae0db20bc215",
        "identifier": [{"use": "official", "system": "http://hl7.org/fhir/sid/pesel"}],
        "name": [{"use": "official", "family": "Jędruszczak", "given": ["Aurelia"]}],
        "telecom": [
            {"system": "phone", "value": "500 939 265", "use": "mobile"},
            {"system": "email", "value": "lkapuscik@example.com", "use": "home"},
        ],
        "gender": "female",
        "birthDate": "2004-11-06",
        "address": [
            {
                "use": "home",
                "line": ["ul. Zwycięstwa 71/11"],
                "city": "Skierniewice",
                "postalCode": "32-835",
                "country": "PL",
            }
        ],
    }

    MOCK_PATIENTS_SEARCH = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 6,
        "entry": [
            {
                "fullUrl": "urn:uuid:d5c62a6e-6f72-469c-99ce-a2419ac9f432",
                "resource": {
                    "resourceType": "Patient",
                    "internal_guid": "d5c62a6e-6f72-469c-99ce-a2419ac9f432",
                    "identifier": [
                        {"use": "official", "system": "http://hl7.org/fhir/sid/pesel"}
                    ],
                    "name": [
                        {
                            "use": "official",
                            "family": "Trochimiuk",
                            "given": ["Ksawery"],
                        }
                    ],
                    "telecom": [
                        {"system": "phone", "value": "780 740 291", "use": "mobile"},
                        {
                            "system": "email",
                            "value": "sebastianpizon@example.org",
                            "use": "home",
                        },
                    ],
                    "gender": "male",
                    "birthDate": "1985-02-09",
                    "address": [
                        {
                            "use": "home",
                            "line": ["ul. Zwycięstwa 980"],
                            "city": "Kwidzyn",
                            "postalCode": "86-529",
                            "country": "PL",
                        }
                    ],
                },
            },
            {
                "fullUrl": "urn:uuid:7be0aac5-9f5d-4667-99ba-18c607d4f6ea",
                "resource": {
                    "resourceType": "Patient",
                    "internal_guid": "7be0aac5-9f5d-4667-99ba-18c607d4f6ea",
                    "identifier": [
                        {"use": "official", "system": "http://hl7.org/fhir/sid/pesel"}
                    ],
                    "name": [{"use": "official", "family": "Waluk", "given": ["Inga"]}],
                    "telecom": [
                        {"system": "phone", "value": "570 679 001", "use": "mobile"},
                        {
                            "system": "email",
                            "value": "mokwamikolaj@example.org",
                            "use": "home",
                        },
                    ],
                    "gender": "female",
                    "birthDate": "2013-12-25",
                    "address": [
                        {
                            "use": "home",
                            "line": ["ulica Dolna 75/89"],
                            "city": "Kraśnik",
                            "postalCode": "46-730",
                            "country": "PL",
                        }
                    ],
                },
            },
            {
                "fullUrl": "urn:uuid:cd55f903-b9e7-4e43-ae19-75fc74971dd2",
                "resource": {
                    "resourceType": "Patient",
                    "internal_guid": "cd55f903-b9e7-4e43-ae19-75fc74971dd2",
                    "identifier": [
                        {"use": "official", "system": "http://hl7.org/fhir/sid/pesel"}
                    ],
                    "name": [
                        {"use": "official", "family": "Łaciak", "given": ["Dariusz"]}
                    ],
                    "telecom": [
                        {"system": "phone", "value": "697 079 084", "use": "mobile"},
                        {
                            "system": "email",
                            "value": "uchmara@example.com",
                            "use": "home",
                        },
                    ],
                    "gender": "male",
                    "birthDate": "1946-04-11",
                    "address": [
                        {
                            "use": "home",
                            "line": ["al. Toruńska 41/89"],
                            "city": "Pszczyna",
                            "postalCode": "60-296",
                            "country": "PL",
                        }
                    ],
                },
            },
            {
                "fullUrl": "urn:uuid:8d30f89b-b0e6-46f0-a8d4-d63c8fe92b5b",
                "resource": {
                    "resourceType": "Patient",
                    "internal_guid": "8d30f89b-b0e6-46f0-a8d4-d63c8fe92b5b",
                    "identifier": [
                        {"use": "official", "system": "http://hl7.org/fhir/sid/pesel"}
                    ],
                    "name": [
                        {"use": "official", "family": "Hejduk", "given": ["Inga"]}
                    ],
                    "telecom": [
                        {
                            "system": "phone",
                            "value": "+48 575 994 136",
                            "use": "mobile",
                        },
                        {
                            "system": "email",
                            "value": "zworoch@example.org",
                            "use": "home",
                        },
                    ],
                    "gender": "female",
                    "birthDate": "2008-03-05",
                    "address": [
                        {
                            "use": "home",
                            "line": ["aleja Zaułek 94/33"],
                            "city": "Śrem",
                            "postalCode": "85-857",
                            "country": "PL",
                        }
                    ],
                },
            },
            {
                "fullUrl": "urn:uuid:9538227f-bb85-400a-bf6e-563fce528142",
                "resource": {
                    "resourceType": "Patient",
                    "internal_guid": "9538227f-bb85-400a-bf6e-563fce528142",
                    "identifier": [
                        {"use": "official", "system": "http://hl7.org/fhir/sid/pesel"}
                    ],
                    "name": [
                        {"use": "official", "family": "Matejczuk", "given": ["Eliza"]}
                    ],
                    "telecom": [
                        {"system": "phone", "value": "665 812 872", "use": "mobile"},
                        {
                            "system": "email",
                            "value": "olgierd26@example.org",
                            "use": "home",
                        },
                    ],
                    "gender": "female",
                    "birthDate": "1959-02-09",
                    "address": [
                        {
                            "use": "home",
                            "line": ["plac Jaśminowa 27/68"],
                            "city": "Radomsko",
                            "postalCode": "68-457",
                            "country": "PL",
                        }
                    ],
                },
            },
            {
                "fullUrl": "urn:uuid:ab758f9b-0298-4823-b144-ae0db20bc215",
                "resource": {
                    "resourceType": "Patient",
                    "internal_guid": "ab758f9b-0298-4823-b144-ae0db20bc215",
                    "identifier": [
                        {"use": "official", "system": "http://hl7.org/fhir/sid/pesel"}
                    ],
                    "name": [
                        {
                            "use": "official",
                            "family": "Jędruszczak",
                            "given": ["Aurelia"],
                        }
                    ],
                    "telecom": [
                        {"system": "phone", "value": "500 939 265", "use": "mobile"},
                        {
                            "system": "email",
                            "value": "lkapuscik@example.com",
                            "use": "home",
                        },
                    ],
                    "gender": "female",
                    "birthDate": "2004-11-06",
                    "address": [
                        {
                            "use": "home",
                            "line": ["ul. Zwycięstwa 71/11"],
                            "city": "Skierniewice",
                            "postalCode": "32-835",
                            "country": "PL",
                        }
                    ],
                },
            },
        ],
    }

    MOCK_PATIENTS_BULK = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 2,
        "entry": [
            {
                "fullUrl": "urn:uuid:8d30f89b-b0e6-46f0-a8d4-d63c8fe92b5b",
                "resource": {
                    "resourceType": "Patient",
                    "internal_guid": "8d30f89b-b0e6-46f0-a8d4-d63c8fe92b5b",
                    "identifier": [
                        {"use": "official", "system": "http://hl7.org/fhir/sid/pesel"}
                    ],
                    "name": [
                        {"use": "official", "family": "Hejduk", "given": ["Inga"]}
                    ],
                    "telecom": [
                        {
                            "system": "phone",
                            "value": "+48 575 994 136",
                            "use": "mobile",
                        },
                        {
                            "system": "email",
                            "value": "zworoch@example.org",
                            "use": "home",
                        },
                    ],
                    "gender": "female",
                    "birthDate": "2008-03-05",
                    "address": [
                        {
                            "use": "home",
                            "line": ["aleja Zaułek 94/33"],
                            "city": "Śrem",
                            "postalCode": "85-857",
                            "country": "PL",
                        }
                    ],
                },
            },
            {
                "fullUrl": "urn:uuid:ab758f9b-0298-4823-b144-ae0db20bc215",
                "resource": {
                    "resourceType": "Patient",
                    "internal_guid": "ab758f9b-0298-4823-b144-ae0db20bc215",
                    "identifier": [
                        {"use": "official", "system": "http://hl7.org/fhir/sid/pesel"}
                    ],
                    "name": [
                        {
                            "use": "official",
                            "family": "Jędruszczak",
                            "given": ["Aurelia"],
                        }
                    ],
                    "telecom": [
                        {"system": "phone", "value": "500 939 265", "use": "mobile"},
                        {
                            "system": "email",
                            "value": "lkapuscik@example.com",
                            "use": "home",
                        },
                    ],
                    "gender": "female",
                    "birthDate": "2004-11-06",
                    "address": [
                        {
                            "use": "home",
                            "line": ["ul. Zwycięstwa 71/11"],
                            "city": "Skierniewice",
                            "postalCode": "32-835",
                            "country": "PL",
                        }
                    ],
                },
            },
        ],
    }

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        user_data: dict[str, str] = TestFixtures.get_test_user_data()
        self.user: User = User.objects.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password="testpass123",
        )
        cache.clear()
        patient_service.mock_mode = False

    def tearDown(self) -> None:
        User.objects.all().delete()
        cache.clear()
        patient_service.mock_mode = MOCK_PATIENT_SERVICE

    @patch("patients.services.requests.get")
    def test_get_patient_success(self, mock_get: Mock) -> None:
        """Test successful patient retrieval with valid GUID."""
        guid = "ab758f9b-0298-4823-b144-ae0db20bc215"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.MOCK_PATIENT_SINGLE
        mock_get.return_value = mock_response

        request: Request = self.factory.get(f"/api/patients/{guid}/")
        force_authenticate(request, user=self.user)

        response: Response = GetPatientView.as_view()(request, guid=guid)

        self.assertEqual(response.status_code, 200)
        self.assertIn("internal_guid", response.data)
        self.assertIn("first_name", response.data)
        self.assertIn("last_name", response.data)
        self.assertEqual(response.data["internal_guid"], guid)
        self.assertEqual(response.data["first_name"], "Aurelia")
        self.assertEqual(response.data["last_name"], "Jędruszczak")

    @patch("patients.services.requests.get")
    def test_get_patient_not_found(self, mock_get: Mock) -> None:
        """Test patient retrieval with non-existent GUID."""
        guid = "99999999-9999-9999-9999-999999999999"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        request: Request = self.factory.get(f"/api/patients/{guid}/")
        force_authenticate(request, user=self.user)

        response: Response = GetPatientView.as_view()(request, guid=guid)

        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "Patient not found.")

    @patch("patients.services.requests.get")
    def test_get_patient_invalid_guid_format(self, mock_get: Mock) -> None:
        """Test patient retrieval with malformed GUID."""
        invalid_guids = [
            "not-a-guid",
            "12345",
            "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "00000000-0000-0000-0000",  # Incomplete GUID
            "00000000-0000-0000-0000-000000000001-extra",  # Too long
        ]

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        for invalid_guid in invalid_guids:
            with self.subTest(guid=invalid_guid):
                request: Request = self.factory.get(f"/api/patients/{invalid_guid}/")
                force_authenticate(request, user=self.user)

                response: Response = GetPatientView.as_view()(
                    request, guid=invalid_guid
                )

                # Invalid GUIDs should return 404 (not found)
                self.assertEqual(response.status_code, 404)

    @patch("patients.services.requests.get")
    def test_get_patient_empty_guid(self, mock_get: Mock) -> None:
        """Test patient retrieval with empty GUID returns 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        request: Request = self.factory.get("/api/patients//")
        force_authenticate(request, user=self.user)

        response: Response = GetPatientView.as_view()(request, guid="")

        self.assertEqual(response.status_code, 404)

    def test_get_patient_unauthenticated(self) -> None:
        """Test patient retrieval without authentication."""
        guid = "00000000-0000-0000-0000-000000000001"
        request: Request = self.factory.get(f"/api/patients/{guid}/")
        # Don't authenticate the request

        response: Response = GetPatientView.as_view()(request, guid=guid)

        self.assertEqual(response.status_code, 401)

    @patch("patients.services.requests.get")
    def test_search_patients_success(self, mock_get: Mock) -> None:
        """Test successful patient search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.MOCK_PATIENTS_SEARCH
        mock_get.return_value = mock_response

        request: Request = self.factory.get("/api/patients/")
        force_authenticate(request, user=self.user)

        response: Response = SearchPatientsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 6)

    @patch("patients.services.requests.get")
    def test_search_patients_with_search_term(self, mock_get: Mock) -> None:
        """Test patient search with search term."""
        search_term = "Aurelia"

        entry = self.MOCK_PATIENTS_SEARCH["entry"]

        assert isinstance(entry, list)

        # Create filtered result with only matching patient
        filtered_bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 1,
            "entry": [entry[-1]],  # type: ignore
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = filtered_bundle
        mock_get.return_value = mock_response

        request: Request = self.factory.get(f"/api/patients/?search={search_term}")
        force_authenticate(request, user=self.user)

        response: Response = SearchPatientsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        patient = response.data[0]
        self.assertTrue(
            search_term.lower() in patient["first_name"].lower()
            or search_term.lower() in patient["last_name"].lower()
        )

    @patch("patients.services.requests.get")
    def test_search_patients_no_results(self, mock_get: Mock) -> None:
        """Test patient search with search term that has no matches."""
        search_term = "NonExistentPatient12345"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 0,
            "entry": [],
        }
        mock_get.return_value = mock_response

        request: Request = self.factory.get(f"/api/patients/?search={search_term}")
        force_authenticate(request, user=self.user)

        response: Response = SearchPatientsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 0)

    @patch("patients.services.requests.get")
    def test_search_patients_empty_search_term(self, mock_get: Mock) -> None:
        """Test patient search with empty search term."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.MOCK_PATIENTS_SEARCH
        mock_get.return_value = mock_response

        request: Request = self.factory.get("/api/patients/?search=")
        force_authenticate(request, user=self.user)

        response: Response = SearchPatientsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    @patch("patients.services.requests.get")
    def test_search_patients_special_characters(self, mock_get: Mock) -> None:
        """Test patient search with special characters in search term."""
        special_chars = ["%", "&", "ą", "ł", "ż"]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 0,
            "entry": [],
        }
        mock_get.return_value = mock_response

        for search_term in special_chars:
            with self.subTest(search_term=search_term):
                request: Request = self.factory.get(
                    f"/api/patients/?search={search_term}"
                )
                force_authenticate(request, user=self.user)

                response: Response = SearchPatientsView.as_view()(request)

                # Should handle gracefully without errors
                self.assertEqual(response.status_code, 200)
                self.assertIsInstance(response.data, list)

    def test_search_patients_unauthenticated(self) -> None:
        """Test patient search without authentication."""
        request: Request = self.factory.get("/api/patients/")
        # Don't authenticate the request

        response: Response = SearchPatientsView.as_view()(request)

        self.assertEqual(response.status_code, 401)


class TestPatientService(TestCase):
    """Test PatientService with mocking and error handling."""

    def setUp(self) -> None:
        self.service = PatientService()
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_parse_fhir_patient_complete_data(self) -> None:
        """Test parsing complete FHIR patient resource."""
        fhir_resource = {
            "internal_guid": "patient-12345",
            "identifier": [
                {"system": "http://hl7.org/fhir/sid/pesel", "value": "90010112345"}
            ],
            "name": [{"family": "Kowalski", "given": ["Jan", "Adam"]}],
            "birthDate": "1990-01-01",
            "gender": "male",
            "telecom": [
                {"system": "phone", "value": "+48123456789"},
                {"system": "email", "value": "jan@example.com"},
            ],
            "address": [
                {
                    "line": ["ul. Przykładowa 1"],
                    "city": "Warszawa",
                    "postalCode": "00-001",
                    "country": "PL",
                }
            ],
        }

        result = self.service._parse_fhir_patient(fhir_resource)

        self.assertEqual(result["internal_guid"], "patient-12345")
        self.assertEqual(result["pesel"], "90010112345")
        self.assertEqual(result["first_name"], "Jan")
        self.assertEqual(result["last_name"], "Kowalski")
        self.assertEqual(result["birth_date"], "1990-01-01")
        self.assertEqual(result["gender"], "male")
        self.assertEqual(result["phone"], "+48123456789")
        self.assertEqual(result["email"], "jan@example.com")
        self.assertEqual(result["address_line"], "ul. Przykładowa 1")
        self.assertEqual(result["city"], "Warszawa")
        self.assertEqual(result["postal_code"], "00-001")
        self.assertEqual(result["country"], "PL")

    def test_parse_fhir_patient_minimal_data(self) -> None:
        """Test parsing FHIR patient with minimal data."""
        fhir_resource = {
            "internal_guid": "minimal",
            "name": [],
            "identifier": [],
            "telecom": [],
            "address": [],
        }

        result = self.service._parse_fhir_patient(fhir_resource)

        self.assertEqual(result["internal_guid"], "minimal")
        self.assertIsNone(result["pesel"])
        self.assertEqual(result["first_name"], "")
        self.assertEqual(result["last_name"], "")
        self.assertIsNone(result["birth_date"])
        self.assertIsNone(result["gender"])
        self.assertIsNone(result["phone"])
        self.assertIsNone(result["email"])
        self.assertIsNone(result["address_line"])
        self.assertIsNone(result["city"])
        self.assertIsNone(result["postal_code"])
        self.assertIsNone(result["country"])

    def test_parse_fhir_patient_empty_data(self) -> None:
        """Test parsing empty FHIR patient resource."""
        fhir_resource: dict = {}

        result = self.service._parse_fhir_patient(fhir_resource)

        self.assertEqual(result["internal_guid"], None)
        self.assertIsNone(result["pesel"])
        self.assertEqual(result["first_name"], "")
        self.assertEqual(result["last_name"], "")

    def test_parse_fhir_patient_no_pesel_identifier(self) -> None:
        """Test parsing FHIR patient without PESEL identifier."""
        fhir_resource = {
            "internal_guid": "patient-no-pesel",
            "identifier": [{"system": "http://other-system.com", "value": "OTHER123"}],
        }

        result = self.service._parse_fhir_patient(fhir_resource)

        self.assertIsNone(result["pesel"])

    def test_parse_fhir_patient_id_without_prefix(self) -> None:
        """Test parsing FHIR patient with ID that doesn't have patient- prefix."""
        fhir_resource = {
            "internal_guid": "12345-no-prefix",
        }

        result = self.service._parse_fhir_patient(fhir_resource)

        self.assertEqual(result["internal_guid"], "12345-no-prefix")

    def test_mock_get_patient_success(self) -> None:
        """Test mock get patient with valid GUID."""
        guid = "00000000-0000-0000-0000-000000000001"
        result = self.service._mock_get_patient(guid)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["internal_guid"], guid)
        self.assertEqual(result["first_name"], "Jan")
        self.assertEqual(result["last_name"], "Kowalski")

    def test_mock_get_patient_not_found(self) -> None:
        """Test mock get patient with invalid GUID."""
        guid = "99999999-9999-9999-9999-999999999999"
        result = self.service._mock_get_patient(guid)

        self.assertIsNone(result)

    def test_mock_search_patients_no_search_term(self) -> None:
        """Test mock search patients without search term."""
        result = self.service._mock_search_patients(None)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["first_name"], "Jan")

    def test_mock_search_patients_matching_first_name(self) -> None:
        """Test mock search patients with matching first name."""
        result = self.service._mock_search_patients("Jan")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["first_name"], "Jan")

    def test_mock_search_patients_matching_last_name(self) -> None:
        """Test mock search patients with matching last name."""
        result = self.service._mock_search_patients("Kowalski")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["last_name"], "Kowalski")

    def test_mock_search_patients_matching_pesel(self) -> None:
        """Test mock search patients with matching PESEL."""
        result = self.service._mock_search_patients("90010112345")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["pesel"], "90010112345")

    def test_mock_search_patients_no_match(self) -> None:
        """Test mock search patients with no matching term."""
        result = self.service._mock_search_patients("NonExistent")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_mock_search_patients_case_insensitive(self) -> None:
        """Test mock search patients is case insensitive."""
        result = self.service._mock_search_patients("JAN")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    @patch("patients.services.MOCK_PATIENT_SERVICE", True)
    def test_get_patient_by_guid_mock_mode(self) -> None:
        """Test get patient by GUID in mock mode."""
        # Force reinitialize service with mock mode
        service = PatientService()
        service.mock_mode = True
        guid = "00000000-0000-0000-0000-000000000001"

        result = service.get_patient_by_guid(guid)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["internal_guid"], guid)

    @patch("patients.services.MOCK_PATIENT_SERVICE", True)
    def test_search_patients_mock_mode(self) -> None:
        """Test search patients in mock mode."""
        service = PatientService()
        service.mock_mode = True

        result = service.search_patients("Jan")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_get_patient_by_guid_api_success(self, mock_get: Mock) -> None:
        """Test get patient by GUID with successful API call."""
        guid = "test-guid-123"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "internal_guid": guid,
            "name": [{"family": "Test", "given": ["Patient"]}],
            "identifier": [],
        }
        mock_get.return_value = mock_response

        service = PatientService()
        result = service.get_patient_by_guid(guid)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["internal_guid"], guid)
        self.assertEqual(result["first_name"], "Patient")
        self.assertEqual(result["last_name"], "Test")

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_get_patient_by_guid_api_not_found(self, mock_get: Mock) -> None:
        """Test get patient by GUID when API returns 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        service = PatientService()
        result = service.get_patient_by_guid("nonexistent-guid")

        self.assertIsNone(result)

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_get_patient_by_guid_api_timeout(self, mock_get: Mock) -> None:
        """Test get patient by GUID when API times out."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

        service = PatientService()

        with self.assertRaises(PatientServiceUnavailableError):
            service.get_patient_by_guid("test-guid")

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_get_patient_by_guid_api_connection_error(self, mock_get: Mock) -> None:
        """Test get patient by GUID when API connection fails."""
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Cannot connect to service"
        )

        service = PatientService()

        with self.assertRaises(PatientServiceUnavailableError):
            service.get_patient_by_guid("test-guid")

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_get_patient_by_guid_api_invalid_json(self, mock_get: Mock) -> None:
        """Test get patient by GUID when API returns invalid JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        service = PatientService()

        with self.assertRaises(PatientServiceResponseError):
            service.get_patient_by_guid("test-guid")

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_search_patients_api_success(self, mock_get: Mock) -> None:
        """Test search patients with successful API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entry": [
                {
                    "resource": {
                        "internal_guid": "patient-1",
                        "name": [{"family": "Doe", "given": ["John"]}],
                    }
                },
                {
                    "resource": {
                        "internal_guid": "patient-2",
                        "name": [{"family": "Smith", "given": ["Jane"]}],
                    }
                },
            ]
        }
        mock_get.return_value = mock_response

        service = PatientService()
        result = service.search_patients("test")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["first_name"], "John")
        self.assertEqual(result[1]["first_name"], "Jane")

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_search_patients_api_empty_results(self, mock_get: Mock) -> None:
        """Test search patients when API returns empty results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": []}
        mock_get.return_value = mock_response

        service = PatientService()
        result = service.search_patients("nonexistent")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_search_patients_api_timeout(self, mock_get: Mock) -> None:
        """Test search patients when API times out."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

        service = PatientService()

        with self.assertRaises(PatientServiceUnavailableError):
            service.search_patients("test")

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_search_patients_api_connection_error(self, mock_get: Mock) -> None:
        """Test search patients when API connection fails."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Cannot connect")

        service = PatientService()

        with self.assertRaises(PatientServiceUnavailableError):
            service.search_patients("test")

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_caching_get_patient(self, mock_get: Mock) -> None:
        """Test that get_patient_by_guid uses cache."""
        guid = "cached-patient-guid"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "internal_guid": guid,
            "name": [{"family": "Cached", "given": ["Patient"]}],
        }
        mock_get.return_value = mock_response

        service = PatientService()

        # First call should hit the API
        result1 = service.get_patient_by_guid(guid)
        self.assertEqual(mock_get.call_count, 1)

        # Second call should use cache
        result2 = service.get_patient_by_guid(guid)
        self.assertEqual(mock_get.call_count, 1)  # Should not increase

        self.assertEqual(result1, result2)

    @override_settings(MOCK_PATIENT_SERVICE=False)
    @patch("patients.services.requests.get")
    def test_caching_search_patients(self, mock_get: Mock) -> None:
        """Test that search_patients uses cache."""
        search_term = "cached"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entry": [
                {
                    "resource": {
                        "internal_guid": "patient-1",
                        "name": [{"family": "Cached", "given": ["Test"]}],
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        service = PatientService()

        # First call should hit the API
        result1 = service.search_patients(search_term)
        self.assertEqual(mock_get.call_count, 1)

        # Second call should use cache
        result2 = service.search_patients(search_term)
        self.assertEqual(mock_get.call_count, 1)  # Should not increase

        self.assertEqual(result1, result2)


class TestPatientErrors(TestCase):
    """Test custom patient error classes."""

    def test_patient_service_error_base(self) -> None:
        """Test base PatientServiceError exception."""
        from patients.errors import PatientServiceError

        error = PatientServiceError("Test error")
        self.assertEqual(str(error), "Test error")

    def test_patient_service_unavailable_error(self) -> None:
        """Test PatientServiceUnavailableError exception."""
        error = PatientServiceUnavailableError("Service unavailable")
        self.assertEqual(str(error), "Service unavailable")

    def test_patient_service_response_error(self) -> None:
        """Test PatientServiceResponseError exception."""
        error = PatientServiceResponseError("Invalid response")
        self.assertEqual(str(error), "Invalid response")


if __name__ == "__main__":
    test_classes = [
        TestPatientViews,
        TestPatientService,
        TestPatientErrors,
    ]
    success = run_tests(test_classes)
    sys.exit(0 if success else 1)
