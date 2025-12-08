import os
from unittest.mock import patch
from io import BytesIO

from django.test import TestCase

from analysis.models import VideoAnalysis, Substance, AnalysisResult
from reports.services.reports import AnalysisReportPDFGenerator
from accounts.models import User

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "larvixon_site.settings")


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

    @patch("reports.services.reports.finders.find")
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

    @patch("reports.services.reports.finders.find")
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
