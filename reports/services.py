import os
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.staticfiles import finders
from reportlab.lib.pagesizes import A4
from patients.services import patient_service
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily


class AnalysisReportPDFGenerator:
    def __init__(self, analysis):
        self.analysis = analysis
        self.buffer = BytesIO()
        self.doc = None
        self.elements = []
        self.styles = getSampleStyleSheet()
        self.font_name = "Helvetica"
        self.font_name_bold = "Helvetica-Bold"

    def generate(self):
        self._setup_document()
        self._register_fonts()
        self._build_content()
        self._build_pdf()
        return self._get_pdf_bytes()

    def _setup_document(self):
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

    def _register_fonts(self):
        font_regular_path = finders.find("fonts/DejaVuSans.ttf")
        font_bold_path = finders.find("fonts/DejaVuSans-Bold.ttf")

        if not font_regular_path or not font_bold_path:
            print("Warning: Font files not found! Using Helvetica.")
            return

        pdfmetrics.registerFont(TTFont("DejaVuSans", font_regular_path))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", font_bold_path))

        registerFontFamily(
            "DejaVuSans",
            normal="DejaVuSans",
            bold="DejaVuSans-Bold",
            italic="DejaVuSans",
            boldItalic="DejaVuSans-Bold",
        )

        self.font_name = "DejaVuSans"
        self.font_name_bold = "DejaVuSans-Bold"

    def _build_content(self):
        self._update_styles()
        self._add_logo()
        self._add_title()
        self._add_metadata()
        self._add_patient_info()
        self._add_feedback_info()
        self._add_substances_table()
        self._add_footer()

    def _update_styles(self):
        self.styles["Normal"].fontName = self.font_name
        self.styles["Title"].fontName = self.font_name_bold

    def _add_logo(self):
        logo_path = finders.find("logo_dark.png")
        if logo_path and os.path.exists(logo_path):
            img = Image(logo_path)
            iw, ih = img.imageWidth, img.imageHeight
            aspect = ih / float(iw)
            width = 5 * cm
            height = width * aspect
            img.drawWidth = width
            img.drawHeight = height
            self.elements.append(img)
            self.elements.append(Spacer(1, 0.5 * cm))

    def _add_title(self):
        title_style = self.styles["Title"]
        self.elements.append(
            Paragraph(f"Analysis #{self.analysis.id} Report", title_style)
        )
        self.elements.append(Spacer(1, 0.5 * cm))

    def _add_metadata(self):
        normal = self.styles["Normal"]

        meta_data = f"""
        <b>Description:</b> {self.analysis.description}<br/>
        <b>Status:</b> {self.analysis.status.capitalize()}<br/>
        """

        if self.analysis.user.first_name or self.analysis.user.last_name:
            full_name = f"{self.analysis.user.first_name} {self.analysis.user.last_name}".strip()
            meta_data += f"<b>Commissioned by:</b> {full_name}<br/>"
        else:
            meta_data += f"<b>Commissioned by:</b> {self.analysis.user.username}<br/>"

        meta_data += f"<b>Created:</b> {self.analysis.created_at.strftime('%Y-%m-%d %H:%M')}<br/>"

        if self.analysis.completed_at:
            meta_data += f"<b>Completed:</b> {self.analysis.completed_at.strftime('%Y-%m-%d %H:%M')}<br/>"

        self.elements.append(Paragraph(meta_data, normal))
        self.elements.append(Spacer(1, 1 * cm))

    def _add_patient_info(self):
        if not self.analysis.patient_guid:
            return

        patient = patient_service.get_patient_by_guid(str(self.analysis.patient_guid))
        if not patient:
            return

        normal = self.styles["Normal"]

        patient_info = f"""
        <b>Patient Details: </b><br/>
        <b>Name:</b> {patient.get('first_name', '')} {patient.get('last_name', '')}<br/>
        """

        if patient.get("pesel"):
            patient_info += f"<b>PESEL:</b> {patient['pesel']}<br/>"

        if patient.get("gender"):
            gender_display = (
                "Male"
                if patient["gender"] == "male"
                else "Female" if patient["gender"] == "female" else patient["gender"]
            )
            patient_info += f"<b>Gender:</b> {gender_display}<br/>"

        if patient.get("birth_date"):
            patient_info += f"<b>Birth Date:</b> {patient['birth_date']}<br/>"

        if patient.get("phone"):
            patient_info += f"<b>Phone:</b> {patient['phone']}<br/>"

        if patient.get("email"):
            patient_info += f"<b>Email:</b> {patient['email']}<br/>"

        self.elements.append(Paragraph(patient_info, normal))
        self.elements.append(Spacer(1, 0.5 * cm))

    def _add_feedback_info(self):
        normal = self.styles["Normal"]

        if self.analysis.actual_substance:
            self.elements.append(
                Paragraph(
                    f"<b>Actual Substance:</b> {self.analysis.actual_substance}",
                    normal,
                )
            )

        if self.analysis.user_feedback:
            self.elements.append(
                Paragraph(
                    f"<b>User Feedback:</b> {self.analysis.user_feedback}", normal
                )
            )

        self.elements.append(Spacer(1, 0.5 * cm))

    def _add_substances_table(self):
        self.elements.append(
            Paragraph("<b>Detected Substances</b>", self.styles["Heading2"])
        )

        data = [["Substance", "Confidence Score"]]
        results = self.analysis.analysis_results.all()

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
                    ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                    ("ALIGN", (1, 1), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        self.elements.append(table)
        self.elements.append(Spacer(1, 1 * cm))

    def _add_footer(self):
        footer_text = f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        self.elements.append(
            Paragraph(
                footer_text,
                ParagraphStyle(name="Footer", fontSize=10, textColor=colors.grey),
            )
        )

    def _build_pdf(self):
        assert self.doc is not None, "Document not initialized."
        self.doc.build(self.elements)

    def _get_pdf_bytes(self):
        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf

    @staticmethod
    def create_http_response(pdf_bytes, analysis_id):
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="analysis_{analysis_id}_report.pdf"'
        )
        return response
