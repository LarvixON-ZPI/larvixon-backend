from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile
from phonenumber_field.serializerfields import PhoneNumberField


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:  # type: ignore[misc]
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "is_new_user",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
            if not user.is_active:
                raise serializers.ValidationError("Account is disabled.")
            attrs["user"] = user
        else:
            raise serializers.ValidationError("Must include email and password.")

        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    phone_number = PhoneNumberField(allow_blank=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:  # type: ignore[misc]
        model = UserProfile
        fields = (
            "profile_picture",
            "bio",
            "phone_number",
            "organization",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:  # type: ignore[misc]
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "is_new_user",
            "profile",
        )
        read_only_fields = ("id", "username", "date_joined")


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class UserStatsSerializer(serializers.Serializer):
    total_analyses = serializers.IntegerField()
    completed_analyses = serializers.IntegerField()
    pending_analyses = serializers.IntegerField()
    processing_analyses = serializers.IntegerField()
    failed_analyses = serializers.IntegerField()


class MFALoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    mfa_code = serializers.CharField(write_only=True, required=False)


class MFAVerifySerializer(serializers.Serializer):
    code = serializers.CharField(
        max_length=6,
        required=True,
        help_text="The 6-digit MFA code from the authenticator app.",
    )
