import os
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from analysis.models import VideoAnalysis
from reportlab.lib.pagesizes import A4
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily


class AnalysisReportSerializer(serializers.Serializer):
    """
    empty serializer for analysis report view to supress warnings
    """

    pass


class AnalysisReportView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AnalysisReportSerializer

    def get(self, request, pk):
        try:
            analysis = VideoAnalysis.objects.select_related("patient").get(
                pk=pk, user=request.user
            )
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

        font_regular_path = finders.find("fonts/DejaVuSans.ttf")
        font_bold_path = finders.find("fonts/DejaVuSans-Bold.ttf")

        if not font_regular_path or not font_bold_path:
            print("Warning: Font files not found! Using Helvetica.")
            font_name = "Helvetica"
            font_name_bold = "Helvetica-Bold"
        else:
            pdfmetrics.registerFont(TTFont("DejaVuSans", font_regular_path))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", font_bold_path))

            registerFontFamily(
                "DejaVuSans",
                normal="DejaVuSans",
                bold="DejaVuSans-Bold",
                italic="DejaVuSans",
                boldItalic="DejaVuSans-Bold",
            )

            font_name = "DejaVuSans"
            font_name_bold = "DejaVuSans-Bold"

        elements = []
        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        normal.fontName = font_name
        title_style = styles["Title"]
        title_style.fontName = font_name_bold
        heading_style = styles["Heading3"]
        heading_style.fontName = font_name_bold

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

        if analysis.patient:
            patient = analysis.patient

            elements.append(Paragraph("Patient Details", heading_style))

            patient_info = f"""
            <b>Name:</b> {patient.first_name} {patient.last_name}<br/>
            <b>Document ID:</b> {patient.document_id}<br/>
            """

            if patient.pesel:
                patient_info += f"<b>PESEL:</b> {patient.pesel}<br/>"

            patient_info += f"<b>Sex:</b> {patient.get_sex_display()}<br/>"

            if patient.age is not None:
                patient_info += (
                    f"<b>Age:</b> {patient.age} (born {patient.birth_date})<br/>"
                )

            if patient.weight_kg:
                patient_info += f"<b>Weight:</b> {patient.weight_kg} kg<br/>"

            if patient.height_cm:
                patient_info += f"<b>Height:</b> {patient.height_cm} cm<br/>"

            elements.append(Paragraph(patient_info, normal))

        elements.append(Spacer(1, 0.5 * cm))

        meta_data = f"""
        <b>Description:</b> {analysis.description}<br/>
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
                        f"{result.confidence_score:.2f}%",
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
                    ("FONTNAME", (0, 0), (-1, 0), font_name_bold),
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
            f'attachment; filename="{analysis.description}_report.pdf"'
        )
        return response
