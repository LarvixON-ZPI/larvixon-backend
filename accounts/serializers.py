from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile
from analysis.models import VideoAnalysis


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(
        write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:  # type: ignore
        model = User
        fields = ('username', 'email', 'password',
                  'password_confirm', 'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        # Create user profile
        UserProfile.objects.create(user=user)
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled.')
            attrs['user'] = user
        else:
            raise serializers.ValidationError(
                'Must include email and password.')

        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile.
    """
    class Meta:  # type: ignore
        model = UserProfile
        fields = ('bio', 'phone_number', 'organization',
                  'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user information.
    """
    profile = UserProfileSerializer(read_only=True)

    class Meta:  # type: ignore
        model = User
        fields = ('id', 'username', 'email', 'first_name',
                  'last_name', 'date_joined', 'profile')
        read_only_fields = ('id', 'username', 'date_joined')


class VideoAnalysisSerializer(serializers.ModelSerializer):
    """
    Serializer for video analysis records.
    """
    user = serializers.StringRelatedField(
        read_only=True)  # type: ignore

    class Meta:  # type: ignore
        model = VideoAnalysis
        fields = ('id', 'user', 'video_name', 'status', 'created_at', 'completed_at',
                  'results', 'confidence_scores', 'actual_substance', 'user_feedback')
        read_only_fields = ('id', 'user', 'created_at', 'completed_at')


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
