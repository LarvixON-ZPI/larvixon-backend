from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from patients.services import patient_service
from patients.serializers import PatientSerializer
from drf_spectacular.utils import extend_schema


class GetPatientView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PatientSerializer

    @extend_schema(operation_id="patient_retrieve")
    def get(self, request, guid):
        patient_data = patient_service.get_patient_by_guid(guid)

        if patient_data is None:
            return Response(
                {"detail": "Patient not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(patient_data, status=status.HTTP_200_OK)
