from typing import Literal
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from analysis.models import VideoAnalysis
from .services import AnalysisReportPDFGenerator


class AnalysisReportSerializer(serializers.Serializer):
    """
    empty serializer for analysis report view to supress warnings
    """

    pass


class AnalysisReportView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AnalysisReportSerializer

    def get(self, request, pk):
        analysis = self._get_analysis(pk, request.user)
        if not isinstance(analysis, VideoAnalysis):
            if analysis == "Not found":
                return Response(
                    {"detail": "Analysis not found or access denied."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            elif analysis == "Not completed":
                return Response(
                    {"detail": "Report available only for completed analyses."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return

        pdf_bytes = self._generate_pdf(analysis)
        return AnalysisReportPDFGenerator.create_http_response(pdf_bytes, analysis.id)

    def _get_analysis(
        self, pk, user
    ) -> VideoAnalysis | Literal["Not found"] | Literal["Not completed"]:
        try:
            analysis: VideoAnalysis = VideoAnalysis.objects.get(pk=pk, user=user)
        except VideoAnalysis.DoesNotExist:
            return "Not found"

        if analysis.status != VideoAnalysis.Status.COMPLETED:
            return "Not completed"

        return analysis

    def _generate_pdf(self, analysis):
        generator = AnalysisReportPDFGenerator(analysis)
        return generator.generate()
