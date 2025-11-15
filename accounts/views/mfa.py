from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

# Drf Spectacular imports
from drf_spectacular.utils import extend_schema, OpenApiResponse

# Allauth MFA imports
from allauth.mfa.utils import is_mfa_enabled
from allauth.mfa import totp
from allauth.mfa.models import Authenticator

# Python Standard Library and third-party utility imports
import pyotp
import qrcode
from io import BytesIO
import base64

# App's local imports
from ..serializers import MFAVerifySerializer
from ..utils import verify_mfa_code


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
        if is_mfa_enabled(request.user):
            return Response(
                {"detail": "MFA is already enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # TOTPDevice instance to generate the secret key
        pyotp_instance = pyotp.TOTP(pyotp.random_base32())
        secret = pyotp_instance.secret.encode()  # Get the secret and encode it

        # Authenticator object with the generated secret
        device = Authenticator.objects.create(
            user=request.user,
            type=Authenticator.Type.TOTP,
            data={"secret": secret.decode()},
        )

        # Generate the QR code URI using the secret
        otp_uri = pyotp_instance.provisioning_uri(
            name=request.user.email, issuer_name="Larvixon"
        )

        img = qrcode.make(otp_uri)
        buf = BytesIO()
        img.save(buf, format="PNG")
        qr_code_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        return Response(
            {
                "qr_code": f"data:image/png;base64,{qr_code_base64}",
                "secret": base64.b32encode(secret).decode(),
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

        is_valid, error_message, device = verify_mfa_code(
            request.user, code, is_confirmed_check=False
        )

        if is_valid:
            if not device.last_used_at:
                device.last_used_at = timezone.now()
                device.save()
                return Response(
                    {"detail": "MFA successfully activated."}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"detail": "MFA device is already confirmed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"detail": error_message}, status=status.HTTP_400_BAD_REQUEST
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
        if not is_mfa_enabled(request.user):
            return Response(
                {"detail": "MFA is not enabled."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            device = Authenticator.objects.get(
                user=request.user, type=Authenticator.Type.TOTP
            )
            device.delete()
        except Authenticator.DoesNotExist:
            pass  # No device to delete

        return Response(
            {"detail": "MFA successfully deactivated."}, status=status.HTTP_200_OK
        )
