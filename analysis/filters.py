import logging

import django_filters
from django.db.models import Max, Q

from patients.services.patients import patient_service
from patients.errors import PatientServiceError
from .models import VideoAnalysis

logger: logging.Logger = logging.getLogger(__name__)


class VideoAnalysisFilter(django_filters.FilterSet):
    substance_name = django_filters.CharFilter(
        field_name="analysis_results__substance__name_en",
        lookup_expr="icontains",
        label="Substance Name (English, partial match)",
    )

    substance_name_pl = django_filters.CharFilter(
        field_name="analysis_results__substance__name_pl",
        lookup_expr="icontains",
        label="Substance Name (Polish, partial match)",
    )

    min_confidence = django_filters.NumberFilter(
        field_name="analysis_results__confidence_score",
        lookup_expr="gte",
        label="Minimum Confidence Score",
    )

    max_confidence = django_filters.NumberFilter(
        field_name="analysis_results__confidence_score",
        lookup_expr="lte",
        label="Maximum Confidence Score",
    )

    substance_and_score = django_filters.CharFilter(
        method="filter_by_substance_and_min_score",
        label="Substance Name for Min Score Filter (e.g., cocaine,95.5)",
    )

    substance_and_score_pl = django_filters.CharFilter(
        method="filter_by_pl_substance_and_min_score",
        label="Substance Name (Polish) for Min Score Filter (e.g., kokaina,95.5)",
    )

    patient_search = django_filters.CharFilter(
        method="filter_by_patient_search",
        label="Patient Search (searches first name, last name, PESEL)",
    )

    class Meta:
        model = VideoAnalysis
        fields = {
            "status": ["exact"],
            "actual_substance": ["exact", "icontains"],
            "description": ["icontains"],
            "created_at": ["date__gte", "date__lte"],
            "completed_at": ["date__gte", "date__lte"],
            "actual_substance": ["exact", "icontains"],
        }

    def filter_by_substance_and_min_score(self, queryset, name, value):
        # example: 'cocaine,95.5'
        try:
            substance_name, min_score_str = value.split(",")
            min_score = float(min_score_str)
        except (ValueError, AttributeError) as e:
            logger.warning(
                f"Invalid substance and score filter format: {value}, error: {e}"
            )
            return queryset

        annotated_qs = queryset.annotate(
            max_confidence_for_substance=Max(
                "analysis_results__confidence_score",
                filter=Q(
                    analysis_results__substance__name_en__icontains=substance_name.strip()
                ),
            )
        )

        return annotated_qs.filter(max_confidence_for_substance__gte=min_score)

    def filter_by_pl_substance_and_min_score(self, queryset, name, value):
        # example: 'kokaina,95.5'
        try:
            substance_name, min_score_str = value.split(",")
            min_score = float(min_score_str)
        except (ValueError, AttributeError) as e:
            logger.warning(
                f"Invalid Polish substance and score filter format: {value}, error: {e}"
            )
            return queryset

        annotated_qs = queryset.annotate(
            max_confidence_for_substance=Max(
                "analysis_results__confidence_score",
                filter=Q(
                    analysis_results__substance__name_pl__icontains=substance_name.strip()
                ),
            )
        )

        return annotated_qs.filter(max_confidence_for_substance__gte=min_score)

    def filter_by_patient_search(self, queryset, name, value):
        if not value:
            return queryset

        try:
            patients = patient_service.search_patients(pesel=value)
        except PatientServiceError as e:
            logger.error(f"Patient service error during search: {e}")
            raise

        if not patients:
            return queryset.none()

        patient_guids = [p["id"] for p in patients if p.get("id")]

        if not patient_guids:
            return queryset.none()

        return queryset.filter(patient_guid__in=patient_guids)
