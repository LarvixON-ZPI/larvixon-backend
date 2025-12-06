from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging

from reports.errors import AnalysisNotCompletedError, AnalysisNotFoundError, ReportError
from reports.services import ReportService
from reports.renderers import PDFRenderer

logger: logging.Logger = logging.getLogger(__name__)


class AnalysisReportView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [PDFRenderer]

    def get(self, request, pk) -> Response:
        """Generate and return PDF report for a specific analysis."""
        report_service = ReportService()
        try:
            bytes = report_service.generate_report(pk, request.user)

            return self.create_response(bytes, pk)
        except AnalysisNotFoundError:
            return Response(
                {"detail": "Analysis not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AnalysisNotCompletedError:
            return Response(
                {"detail": "Report available only for completed analyses."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ReportError:
            return Response(
                {"detail": "Failed to generate report."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def create_response(pdf_bytes, analysis_id) -> Response:
        response = Response(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="analysis_{analysis_id}_report.pdf"'
        )
        return response
