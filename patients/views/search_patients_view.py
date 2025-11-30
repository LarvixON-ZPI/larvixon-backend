from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from patients.services import patient_service
from patients.serializers import PatientSerializer


class SearchPatientsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PatientSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="first_name",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter patients by first name",
                required=False,
            ),
            OpenApiParameter(
                name="last_name",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter patients by last name",
                required=False,
            ),
            OpenApiParameter(
                name="pesel",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter patients by PESEL",
                required=False,
            ),
        ],
    )
    def get(self, request):
        first_name = request.query_params.get("first_name", None)
        last_name = request.query_params.get("last_name", None)
        pesel = request.query_params.get("pesel", None)

        patients = patient_service.search_patients(
            first_name=first_name, last_name=last_name, pesel=pesel
        )

        return Response(patients, status=status.HTTP_200_OK)
