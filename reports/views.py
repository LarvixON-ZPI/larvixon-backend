import os
from django.shortcuts import render

# Create your views here.
from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from analysis.models import VideoAnalysis
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Spacer,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.contrib.staticfiles import finders


class AnalysisReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            analysis = VideoAnalysis.objects.get(pk=pk, user=request.user)
        except VideoAnalysis.DoesNotExist:
            return Response(
                {"detail": "Analysis not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if analysis.status != VideoAnalysis.Status.COMPLETED:
            return Response(
                {"detail": "Report available only for completed analyses."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        title_style = styles["Title"]

        logo_path = finders.find("logo_dark.png")
        if logo_path and os.path.exists(logo_path):
            img = Image(logo_path)
            iw, ih = img.imageWidth, img.imageHeight
            aspect = ih / float(iw)
            width = 5 * cm
            height = width * aspect
            img.drawWidth = width
            img.drawHeight = height
            elements.append(img)
            elements.append(Spacer(1, 0.5 * cm))

        elements.append(Paragraph(f"Analysis #{analysis.id} Report", title_style))
        elements.append(Spacer(1, 0.5 * cm))

        meta_data = f"""
        <b>Title:</b> {analysis.title}<br/>
        <b>Status:</b> {analysis.status.capitalize()}<br/>
        """

        if analysis.user.first_name or analysis.user.last_name:
            full_name = f"{analysis.user.first_name} {analysis.user.last_name}".strip()
            meta_data += f"<b>Commissioned by:</b> {full_name}<br/>"
        else:
            meta_data += f"<b>Commissioned by:</b> {analysis.user.username}<br/>"

        meta_data += (
            f"<b>Created:</b> {analysis.created_at.strftime('%Y-%m-%d %H:%M')}<br/>"
        )

        if analysis.completed_at:
            meta_data += f"<b>Completed:</b> {analysis.completed_at.strftime('%Y-%m-%d %H:%M')}<br/>"

        elements.append(Paragraph(meta_data, normal))
        elements.append(Spacer(1, 0.5 * cm))

        if analysis.actual_substance:
            elements.append(
                Paragraph(
                    f"<b>Actual Substance:</b> {analysis.actual_substance}", normal
                )
            )
        if analysis.user_feedback:
            elements.append(
                Paragraph(f"<b>User Feedback:</b> {analysis.user_feedback}", normal)
            )
        elements.append(Spacer(1, 0.5 * cm))

        elements.append(Paragraph("<b>Detected Substances</b>", styles["Heading2"]))
        data = [["Substance", "Confidence Score"]]

        results = analysis.analysis_results.all()
        if results.exists():
            for result in results:
                data.append(
                    [
                        result.substance.name_en,
                        f"{result.confidence_score:.2f}",
                    ]
                )
        else:
            data.append(["No substances detected.", "", ""])

        table = Table(data, colWidths=[7 * cm, 4 * cm, 5 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 1 * cm))

        footer_text = f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        elements.append(
            Paragraph(
                footer_text,
                ParagraphStyle(name="Footer", fontSize=10, textColor=colors.grey),
            )
        )

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{analysis.title}_report.pdf"'
        )
        return response
