import django_filters
from django.db.models import Max, Q
from .models import VideoAnalysis


class VideoAnalysisFilter(django_filters.FilterSet):
    substance_name = django_filters.CharFilter(
        field_name="analysis_results__substance__name_en",
        lookup_expr="icontains",
        label="Substance Name (English, partial match)",
    )

    substance_name = django_filters.CharFilter(
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

    class Meta:
        model = VideoAnalysis
        fields = {
            "status": ["exact"],
            "actual_substance": ["exact", "icontains"],
            "title": ["exact", "icontains"],
            "created_at": ["date__gte", "date__lte"],
            "completed_at": ["date__gte", "date__lte"],
            "actual_substance": ["exact", "icontains"],
        }

    def filter_by_substance_and_min_score(self, queryset, name, value):
        # example: 'cocaine,95.5'
        try:
            substance_name, min_score_str = value.split(",")
            min_score = float(min_score_str)
        except (ValueError, AttributeError):
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
        except (ValueError, AttributeError):
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
