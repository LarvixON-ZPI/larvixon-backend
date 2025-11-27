import os
from datetime import date
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from io import BytesIO

from analysis.models import VideoAnalysis, Substance, AnalysisResult
from reports.services import AnalysisReportPDFGenerator
from accounts.models import User

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "larvixon_site.settings")

import django

django.setup()


class ReportBasicTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
        self.substance = Substance.objects.create(name_en="Cocaine", name_pl="Kokaina")

    def tearDown(self):
        VideoAnalysis.objects.all().delete()
        User.objects.all().delete()
        Substance.objects.all().delete()

    def test_report_not_found(self):

        url = reverse("reports:analysis-report", args=[999999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"], "Analysis not found or access denied."
        )

    def test_report_not_completed(self):

        analysis = VideoAnalysis.objects.create(
            user=self.user,
            description="Pending analysis",
            status=VideoAnalysis.Status.PENDING,
        )

        url = reverse("reports:analysis-report", args=[analysis.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"], "Report available only for completed analyses."
        )

    def test_report_access_denied(self):

        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        analysis = VideoAnalysis.objects.create(
            user=other_user,
            description="Other user's analysis",
            status=VideoAnalysis.Status.COMPLETED,
        )

        url = reverse("reports:analysis-report", args=[analysis.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["detail"], "Analysis not found or access denied."
        )

    def test_unauthenticated_access(self):

        analysis = VideoAnalysis.objects.create(
            user=self.user,
            description="Test analysis",
            status=VideoAnalysis.Status.COMPLETED,
        )

        self.client.force_authenticate(user=None)
        url = reverse("reports:analysis-report", args=[analysis.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("reports.services.finders.find")
    def test_successful_report_generation(self, mock_find):

        mock_find.return_value = None

        analysis = VideoAnalysis.objects.create(
            user=self.user,
            description="Completed analysis",
            status=VideoAnalysis.Status.COMPLETED,
        )

        url = reverse("reports:analysis-report", args=[analysis.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(
            f"analysis_{analysis.id}_report.pdf", response["Content-Disposition"]
        )
        self.assertTrue(response.content.startswith(b"%PDF"))


class ReportPDFGeneratorTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.substance = Substance.objects.create(name_en="Cocaine", name_pl="Kokaina")

    def tearDown(self):
        VideoAnalysis.objects.all().delete()
        User.objects.all().delete()
        Substance.objects.all().delete()

    def test_pdf_generator_initialization(self):

        analysis = VideoAnalysis.objects.create(
            user=self.user,
            description="Test analysis",
            status=VideoAnalysis.Status.COMPLETED,
        )

        generator = AnalysisReportPDFGenerator(analysis)
        self.assertIsNotNone(generator)
        self.assertEqual(generator.analysis, analysis)
        self.assertIsInstance(generator.buffer, BytesIO)

    def test_http_response_creation(self):

        pdf_bytes = b"fake pdf content"
        analysis_id = 123

        response = AnalysisReportPDFGenerator.create_http_response(
            pdf_bytes, analysis_id
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(
            f"analysis_{analysis_id}_report.pdf", response["Content-Disposition"]
        )
        self.assertEqual(response.content, pdf_bytes)

    @patch("reports.services.finders.find")
    def test_pdf_generation_without_patient(self, mock_find):

        mock_find.return_value = None

        analysis = VideoAnalysis.objects.create(
            user=self.user,
            description="Analysis without patient",
            status=VideoAnalysis.Status.COMPLETED,
        )

        AnalysisResult.objects.create(
            analysis=analysis, substance=self.substance, confidence_score=85.0
        )

        generator = AnalysisReportPDFGenerator(analysis)
        pdf_bytes = generator.generate()

        self.assertIsNotNone(pdf_bytes)
        self.assertGreater(len(pdf_bytes), 0)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    @patch("reports.services.finders.find")
    def test_pdf_generation_with_multiple_substances(self, mock_find):

        mock_find.return_value = None

        amphetamine = Substance.objects.create(
            name_en="Amphetamine", name_pl="Amfetamina"
        )

        analysis = VideoAnalysis.objects.create(
            user=self.user,
            description="Multi-substance analysis",
            status=VideoAnalysis.Status.COMPLETED,
        )

        AnalysisResult.objects.create(
            analysis=analysis, substance=self.substance, confidence_score=95.5
        )
        AnalysisResult.objects.create(
            analysis=analysis, substance=amphetamine, confidence_score=78.3
        )

        generator = AnalysisReportPDFGenerator(analysis)
        pdf_bytes = generator.generate()

        self.assertIsNotNone(pdf_bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Verify results are present
        results = analysis.analysis_results.all()
        self.assertEqual(results.count(), 2)


class ReportComprehensiveTest(APITestCase):

    def setUp(self):
        # Create user with full details
        self.user = User.objects.create_user(
            username="drsmith",
            email="drsmith@hospital.com",
            password="securepass123",
            first_name="John",
            last_name="Smith",
        )
        self.client.force_authenticate(user=self.user)

        # Mock patient GUID for testing
        self.patient_guid = "00000000-0000-0000-0000-000000000001"

        # Create substances
        self.cocaine = Substance.objects.create(name_en="Cocaine", name_pl="Kokaina")
        self.amphetamine = Substance.objects.create(
            name_en="Amphetamine", name_pl="Amfetamina"
        )
        self.methamphetamine = Substance.objects.create(
            name_en="Methamphetamine", name_pl="Metamfetamina"
        )

    def tearDown(self):
        VideoAnalysis.objects.all().delete()
        AnalysisResult.objects.all().delete()
        Substance.objects.all().delete()
        User.objects.all().delete()

    @patch("reports.services.patient_service.get_patient_by_guid")
    @patch("reports.services.finders.find")
    def test_comprehensive_report_generation_happy_path(
        self, mock_find, mock_get_patient
    ):
        # Mock static file finding to avoid filesystem dependencies
        mock_find.return_value = None

        # Mock patient service to return patient data
        mock_get_patient.return_value = {
            "internal_guid": self.patient_guid,
            "pesel": "90010112345",
            "first_name": "Jane",
            "last_name": "Doe",
            "birth_date": "1990-01-01",
            "gender": "female",
        }

        # Create completed analysis with all fields
        analysis = VideoAnalysis.objects.create(
            user=self.user,
            patient_guid=self.patient_guid,
            description="Full substance screening test",
            status=VideoAnalysis.Status.COMPLETED,
            actual_substance="Cocaine",
            user_feedback="Patient showed typical cocaine use symptoms",
        )

        # Add multiple analysis results
        AnalysisResult.objects.create(
            analysis=analysis, substance=self.cocaine, confidence_score=95.5
        )
        AnalysisResult.objects.create(
            analysis=analysis, substance=self.amphetamine, confidence_score=78.3
        )
        AnalysisResult.objects.create(
            analysis=analysis, substance=self.methamphetamine, confidence_score=45.2
        )

        # Test API endpoint
        url = reverse("reports:analysis-report", args=[analysis.id])
        response = self.client.get(url)

        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(
            f"analysis_{analysis.id}_report.pdf", response["Content-Disposition"]
        )

        # Verify PDF content is not empty
        self.assertIsNotNone(response.content)
        self.assertGreater(len(response.content), 0)

        # Verify it's a valid PDF (starts with PDF magic number)
        self.assertTrue(response.content.startswith(b"%PDF"))

        # Test PDF generator directly for more detailed checks
        generator = AnalysisReportPDFGenerator(analysis)
        pdf_bytes = generator.generate()

        # Verify PDF structure
        self.assertIsNotNone(pdf_bytes)
        self.assertGreater(len(pdf_bytes), 1000)  # Should be reasonably sized
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Verify analysis was fetched correctly with related data
        analysis_from_db = VideoAnalysis.objects.get(pk=analysis.id)
        self.assertEqual(str(analysis_from_db.patient_guid), self.patient_guid)
        self.assertEqual(analysis_from_db.user.first_name, "John")
        self.assertEqual(analysis_from_db.user.last_name, "Smith")

        # Verify all analysis results are present
        results = analysis.analysis_results.all()
        self.assertEqual(results.count(), 3)

        # Verify substances are ordered correctly or all present
        substance_names = [result.substance.name_en for result in results]
        self.assertIn("Cocaine", substance_names)
        self.assertIn("Amphetamine", substance_names)
        self.assertIn("Methamphetamine", substance_names)

        # Verify confidence scores
        cocaine_result = results.get(substance=self.cocaine)
        self.assertEqual(cocaine_result.confidence_score, 95.5)

        # Verify feedback fields
        self.assertEqual(analysis.actual_substance, "Cocaine")
        self.assertIn("symptoms", analysis.user_feedback)
