import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiResponse

import base64

from accounts.errors import (
    MFAAlreadyEnabledError,
    MFANotEnabledError,
    MFADeviceNotFoundError,
    InvalidMFACodeError,
)
from accounts.services.mfa import MFAService

from ..serializers import MFAVerifySerializer

logger: logging.Logger = logging.getLogger(__name__)


class MFASetupView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Start 2FA setup for the authenticated user",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "qr_code": {"type": "string"},
                    "secret": {"type": "string"},
                },
            },
            400: {"description": "MFA is already enabled"},
        },
        tags=["Authentication"],
    )
    def get(self, request):
        try:
            _, secret, qr_code_base64 = MFAService.setup(request.user)
        except MFAAlreadyEnabledError:
            logger.warning(
                f"User {request.user.pk} attempted to setup MFA but it is already enabled."
            )
            return Response(
                {"detail": "MFA is already enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "qr_code": f"data:image/png;base64,{qr_code_base64}",
                "secret": secret,
            },
            status=status.HTTP_200_OK,
        )


class MFAVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Verify 2FA code and activate 2FA",
        request=MFAVerifySerializer,
        responses={
            200: OpenApiResponse(description="MFA successfully activated."),
            400: OpenApiResponse(description="Invalid code."),
        },
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        try:
            MFAService.activate_mfa_device(request.user, code)
            return Response(
                {"detail": "MFA successfully activated."}, status=status.HTTP_200_OK
            )
        except MFADeviceNotFoundError:
            logger.warning(f"No MFA device found for user {request.user.pk}")
            return Response(
                {"detail": "No MFA device found."}, status=status.HTTP_400_BAD_REQUEST
            )
        except InvalidMFACodeError as e:
            logger.warning(f"Invalid MFA code for user {request.user.pk}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except MFAAlreadyEnabledError:
            logger.warning(f"MFA device already confirmed for user {request.user.pk}")
            return Response(
                {"detail": "MFA device is already confirmed."},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(
    summary="Deactivate 2FA for the authenticated user",
    request=None,
    responses={
        200: {"detail": "MFA successfully deactivated."},
        400: {"detail": "MFA is not enabled."},
    },
    tags=["Authentication"],
)
class MFADeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            MFAService.deactivate_mfa(request.user)
            return Response(
                {"detail": "MFA successfully deactivated."}, status=status.HTTP_200_OK
            )
        except MFANotEnabledError:
            logger.warning(
                f"User {request.user.pk} attempted to deactivate MFA but it's not enabled"
            )
            return Response(
                {"detail": "MFA is not enabled."}, status=status.HTTP_400_BAD_REQUEST
            )
        except MFADeviceNotFoundError:
            logger.error(f"MFA enabled but device not found for user {request.user.pk}")
            return Response(
                {"detail": "MFA device not found."}, status=status.HTTP_400_BAD_REQUEST
            )
