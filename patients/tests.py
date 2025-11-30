import sys
from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from django.core.cache import cache
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.request import Request
from rest_framework.response import Response
import requests

from accounts.models import User
from patients.views.get_patient_view import GetPatientView
from patients.views.search_patients_view import SearchPatientsView
from patients.services import patient_service
from patients.errors import (
    PatientServiceUnavailableError,
    PatientServiceResponseError,
)
from larvixon_site.settings import MOCK_PATIENT_SERVICE
from tests.common import TestFixtures, run_tests


class TestPatientViews(APITestCase):
    """Test patient API views with authentication and edge cases."""

    # Mock FHIR data fixtures
    MOCK_PATIENT_SINGLE = {
        "resourceType": "Patient",
        "id": "ab758f9b-0298-4823-b144-ae0db20bc215",
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
                    "id": "d5c62a6e-6f72-469c-99ce-a2419ac9f432",
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
                    "id": "7be0aac5-9f5d-4667-99ba-18c607d4f6ea",
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
                    "id": "cd55f903-b9e7-4e43-ae19-75fc74971dd2",
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
                    "id": "8d30f89b-b0e6-46f0-a8d4-d63c8fe92b5b",
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
                    "id": "9538227f-bb85-400a-bf6e-563fce528142",
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
                    "id": "ab758f9b-0298-4823-b144-ae0db20bc215",
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
                    "id": "8d30f89b-b0e6-46f0-a8d4-d63c8fe92b5b",
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
                    "id": "ab758f9b-0298-4823-b144-ae0db20bc215",
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

    def tearDown(self) -> None:
        User.objects.all().delete()
        cache.clear()

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
        self.assertIn("id", response.data)
        self.assertIn("first_name", response.data)
        self.assertIn("last_name", response.data)
        self.assertEqual(response.data["id"], guid)
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
        TestPatientErrors,
    ]
    success = run_tests(test_classes)
    sys.exit(0 if success else 1)
