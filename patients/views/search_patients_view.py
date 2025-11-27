from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from patients.services import patient_service


class SearchPatientsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search term to filter patients by name, PESEL, or other fields",
                required=False,
            ),
        ],
    )
    def get(self, request):
        search_term = request.query_params.get("search", None)

        patients = patient_service.search_patients(search_term)

        return Response(patients, status=status.HTTP_200_OK)
