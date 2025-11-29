import os
import shutil
from django.urls import reverse
from django.utils import timezone
import datetime
from rest_framework import status
from rest_framework.test import APITestCase
from larvixon_site import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Substance, AnalysisResult, User, VideoAnalysis
import uuid
from unittest.mock import patch
from django.test import override_settings


@override_settings(MOCK_PATIENT_SERVICE=False)
class VideoAnalysisTest(APITestCase):
    def setUp(self):
        # Mock patient service data
        self.mock_patient_data1 = {
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

        self.mock_patient_data2 = {
            "id": "00000000-0000-0000-0000-000000000002",
            "pesel": "85050512345",
            "first_name": "Jan",
            "last_name": "Kowalski",
            "birth_date": "1985-05-05",
            "gender": "male",
            "phone": "+48987654321",
            "email": "jan.kowalski2@example.com",
            "address_line": "ul. Testowa 2",
            "city": "Kraków",
            "postal_code": "30-001",
            "country": "PL",
        }

        # Patch the patient service methods
        self.patcher_get_patient = patch(
            "patients.services.patient_service.get_patient_by_guid"
        )
        self.patcher_search_patients = patch(
            "patients.services.patient_service.search_patients"
        )
        self.patcher_get_patients_by_guids = patch(
            "patients.services.patient_service.get_patients_by_guids"
        )

        self.mock_get_patient = self.patcher_get_patient.start()
        self.mock_search_patients = self.patcher_search_patients.start()
        self.mock_get_patients_by_guids = self.patcher_get_patients_by_guids.start()

        # Configure mock for get_patient_by_guid to return appropriate patient based on GUID
        def mock_get_patient_side_effect(guid):
            if guid == "00000000-0000-0000-0000-000000000001":
                return self.mock_patient_data1
            elif guid == "00000000-0000-0000-0000-000000000002":
                return self.mock_patient_data2
            return None

        self.mock_get_patient.side_effect = mock_get_patient_side_effect

        # Configure mock for get_patients_by_guids to return appropriate patients based on GUIDs
        def mock_get_patients_by_guids_side_effect(guids):
            results = {}
            for guid in guids:
                guid_str = str(guid)
                if guid_str == "00000000-0000-0000-0000-000000000001":
                    results[guid_str] = self.mock_patient_data1
                elif guid_str == "00000000-0000-0000-0000-000000000002":
                    results[guid_str] = self.mock_patient_data2
            return results

        self.mock_get_patients_by_guids.side_effect = (
            mock_get_patients_by_guids_side_effect
        )

        # Configure mock for search_patients to return appropriate results based on search term
        def mock_search_patients_side_effect(search_term=None):
            if not search_term:
                return [self.mock_patient_data1, self.mock_patient_data2]

            search_lower = search_term.lower()
            results = []

            # Check if search matches patient 1
            if (
                search_lower in self.mock_patient_data1["first_name"].lower()
                or search_lower in self.mock_patient_data1["last_name"].lower()
                or (
                    self.mock_patient_data1["pesel"]
                    and search_lower in self.mock_patient_data1["pesel"]
                )
            ):
                results.append(self.mock_patient_data1)

            # Check if search matches patient 2
            if (
                search_lower in self.mock_patient_data2["first_name"].lower()
                or search_lower in self.mock_patient_data2["last_name"].lower()
                or (
                    self.mock_patient_data2["pesel"]
                    and search_lower in self.mock_patient_data2["pesel"]
                )
            ):
                results.append(self.mock_patient_data2)

            return results

        self.mock_search_patients.side_effect = mock_search_patients_side_effect

        # User 1
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # User 2
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )

        self.analysis_list_url = reverse("analysis:analysis-list")

        # Create patient GUIDs (simulating patients in Patient Service)
        self.patient_guid1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.patient_guid2 = uuid.UUID("00000000-0000-0000-0000-000000000002")

        # Create Substances
        self.substance1 = Substance.objects.create(name_en="Cocaine")
        self.substance2 = Substance.objects.create(name_en="Morphine")

        # Create Analyses for self.user
        video_content = b"fake video content"

        # Analysis 1: Completed, has Cocaine and some Morphine
        self.analysis1 = VideoAnalysis.objects.create(
            user=self.user,
            description="Cocaine Test",
            video=SimpleUploadedFile(
                "test_video1.mp4", video_content, content_type="video/mp4"
            ),
            status=VideoAnalysis.Status.COMPLETED,
            patient_guid=self.patient_guid1,
        )
        AnalysisResult.objects.create(
            analysis=self.analysis1, substance=self.substance1, confidence_score=0.95
        )
        AnalysisResult.objects.create(
            analysis=self.analysis1, substance=self.substance2, confidence_score=0.55
        )

        self.analysis1.created_at = timezone.now() - datetime.timedelta(days=2)
        self.analysis1.save()

        # Analysis 2: Completed, has Morphine and some Cocaine
        self.analysis2 = VideoAnalysis.objects.create(
            user=self.user,
            description="A Morphine Video",
            video=SimpleUploadedFile(
                "test_video2.mp4", video_content, content_type="video/mp4"
            ),
            status=VideoAnalysis.Status.COMPLETED,
            patient_guid=self.patient_guid2,
        )
        AnalysisResult.objects.create(
            analysis=self.analysis2, substance=self.substance2, confidence_score=0.80
        )
        AnalysisResult.objects.create(
            analysis=self.analysis2, substance=self.substance1, confidence_score=0.60
        )

        self.analysis2.created_at = timezone.now() - datetime.timedelta(days=1)
        self.analysis2.save()

        # Analysis 3: Pending, no results yet
        self.analysis3 = VideoAnalysis.objects.create(
            user=self.user,
            description="Surprise Analysis",
            video=SimpleUploadedFile(
                "test_video3.mp4", video_content, content_type="video/mp4"
            ),
            status=VideoAnalysis.Status.PENDING,
            created_at=timezone.now(),
            patient_guid=None,
        )

        # Analysis 4: Belongs to other_user
        self.analysis4_other_user = VideoAnalysis.objects.create(
            user=self.other_user,
            description="Other User's Video",
            video=SimpleUploadedFile(
                "test_video4.mp4", video_content, content_type="video/mp4"
            ),
            status=VideoAnalysis.Status.FAILED,
        )

    def test_get_analysis_list(self):
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    def test_create_analysis(self):
        fake_video = SimpleUploadedFile(
            "new_video.mp4", b"fake video content", content_type="video/mp4"
        )

        payload = {
            "description": "New Video Test",
            "video": fake_video,
        }

        self.assertEqual(VideoAnalysis.objects.count(), 4)

        response = self.client.post(self.analysis_list_url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VideoAnalysis.objects.count(), 5)
        new_analysis = VideoAnalysis.objects.get(id=response.data["id"])
        video_name = os.path.basename(new_analysis.video.name)
        self.assertEqual(video_name, "new_video.mp4")

    def test_create_analysis_with_patient(self):
        fake_video = SimpleUploadedFile(
            "patient_video.mp4", b"content", content_type="video/mp4"
        )
        payload = {
            "description": "Analysis for Patient 1",
            "video": fake_video,
            "patient_guid": str(self.patient_guid1),
        }

        response = self.client.post(self.analysis_list_url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_analysis = VideoAnalysis.objects.get(id=response.data["id"])
        self.assertEqual(new_analysis.patient_guid, self.patient_guid1)

    def test_get_analysis_detail_includes_patient(self):
        detail_url = reverse("analysis:analysis-detail", args=[self.analysis1.id])
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("patient_details", response.data)
        # Mock patient service returns same patient for any GUID
        self.assertEqual(response.data["patient_details"]["last_name"], "Kowalski")
        self.assertEqual(response.data["patient_details"]["pesel"], "90010112345")

    def test_delete_analysis(self):
        analysis_to_delete = self.analysis1
        analysis_id = analysis_to_delete.id
        video_path = analysis_to_delete.video.path

        self.assertTrue(os.path.exists(video_path))

        detail_url = reverse("analysis:analysis-detail", args=[analysis_id])
        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(VideoAnalysis.DoesNotExist):
            VideoAnalysis.objects.get(id=analysis_id)

        self.assertFalse(os.path.exists(video_path))

    def test_get_analysis_detail(self):
        detail_url = reverse("analysis:analysis-detail", args=[self.analysis1.id])
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("video_name", response.data)
        self.assertTrue(response.data["video_name"].endswith("test_video1.mp4"))

    def test_update_analysis(self):
        detail_url = reverse("analysis:analysis-detail", args=[self.analysis1.id])
        payload = {
            "actual_substance": "cocaine",
            "user_feedback": "The analysis was accurate",
        }
        response = self.client.patch(detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.analysis1.refresh_from_db()
        self.assertEqual(self.analysis1.actual_substance, "cocaine")

    def test_user_stats(self):
        stats_url = reverse("accounts:user-stats")
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_analyses"], 3)
        self.assertEqual(response.data["completed_analyses"], 2)
        self.assertEqual(response.data["pending_analyses"], 1)

    # --- Filter Tests ---

    def test_filter_by_status(self):
        response = self.client.get(self.analysis_list_url, {"status": "completed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {self.analysis1.id, self.analysis2.id})

    def test_filter_by_description_icontains(self):
        response = self.client.get(
            self.analysis_list_url, {"description__icontains": "video"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis2.id)

    def test_filter_by_related_substance_name(self):
        response = self.client.get(
            self.analysis_list_url, {"substance_name": "Cocaine"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {self.analysis1.id, self.analysis2.id})

    def test_filter_by_min_confidence(self):
        response = self.client.get(self.analysis_list_url, {"min_confidence": 0.90})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis1.id)

    def test_filter_by_custom_substance_and_score(self):
        response = self.client.get(
            self.analysis_list_url, {"substance_and_score": "Cocaine,0.9"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis1.id)

    def test_filter_by_custom_substance_and_score_no_match(self):
        response = self.client.get(
            self.analysis_list_url, {"substance_and_score": "Morphine,0.9"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    # --- Patient Filter Tests ---

    def test_filter_by_patient_search_last_name(self):
        # Mock patient service will return the same mock patient for any search
        # Since both analyses have patient GUIDs, they will both match
        response = self.client.get(
            self.analysis_list_url, {"patient_search": "Kowalski"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Mock service returns same patient for all searches, so both analyses match
        self.assertEqual(len(response.data["results"]), 2)

    def test_filter_by_patient_search_first_name(self):
        response = self.client.get(self.analysis_list_url, {"patient_search": "Jan"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Mock service returns same patient for all searches that match
        self.assertEqual(len(response.data["results"]), 2)

    def test_filter_by_patient_search_pesel(self):
        response = self.client.get(
            self.analysis_list_url, {"patient_search": "90010112345"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_filter_by_patient_search_no_match(self):
        response = self.client.get(
            self.analysis_list_url, {"patient_search": "NonExistent"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Mock patient service won't match this
        self.assertEqual(len(response.data["results"]), 0)

    # --- Ordering Tests ---

    def test_ordering_by_description_ascending(self):
        response = self.client.get(self.analysis_list_url, {"ordering": "description"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        descriptions = [item["description"] for item in response.data["results"]]
        self.assertEqual(
            descriptions, ["A Morphine Video", "Cocaine Test", "Surprise Analysis"]
        )

    def test_ordering_by_description_descending(self):
        response = self.client.get(self.analysis_list_url, {"ordering": "-description"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        descriptions = [item["description"] for item in response.data["results"]]
        self.assertEqual(
            descriptions, ["Surprise Analysis", "Cocaine Test", "A Morphine Video"]
        )

    def test_default_ordering_created_at_descending(self):
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [self.analysis3.id, self.analysis2.id, self.analysis1.id])

    # --- Permission Tests ---

    def test_get_list_unauthenticated(self):
        self.client.force_authenticate(user=None)  # Log out
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_unauthenticated(self):
        self.client.force_authenticate(user=None)
        payload = {"description": "Should Fail"}
        response = self.client.post(self.analysis_list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_see_other_users_analysis_list(self):
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)
        ids = {item["id"] for item in response.data["results"]}
        self.assertNotIn(self.analysis4_other_user.id, ids)

    def test_user_cannot_access_other_users_analysis_detail(self):
        detail_url = reverse(
            "analysis:analysis-detail", args=[self.analysis4_other_user.id]
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_update_other_users_analysis(self):
        detail_url = reverse(
            "analysis:analysis-detail", args=[self.analysis4_other_user.id]
        )
        response = self.client.patch(detail_url, {"description": "hacked"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_delete_other_users_analysis(self):
        detail_url = reverse(
            "analysis:analysis-detail", args=[self.analysis4_other_user.id]
        )
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Validation Tests ---

    def test_create_analysis_invalid_file_type(self):
        fake_text_file = SimpleUploadedFile(
            "not_a_video.txt", b"this is text", content_type="text/plain"
        )
        payload = {
            "description": "Text File Test",
            "video": fake_text_file,
        }
        response = self.client.post(self.analysis_list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_analysis_invalid_data(self):
        detail_url = reverse("analysis:analysis-detail", args=[self.analysis1.id])
        payload = {
            "status": "an-invalid-choice",
        }
        response = self.client.patch(detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    # --- ID List Endpoint Tests ---

    def test_get_analysis_id_list(self):
        id_list_url = reverse("analysis:analysis-id-list")
        response = self.client.get(id_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0].keys(), {"id"})

    def test_get_analysis_id_list_filtered(self):
        id_list_url = reverse("analysis:analysis-id-list")
        response = self.client.get(id_list_url, {"status": "pending"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis3.id)

    def tearDown(self):
        # Stop all patchers
        self.patcher_get_patient.stop()
        self.patcher_search_patients.stop()
        self.patcher_get_patients_by_guids.stop()

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
