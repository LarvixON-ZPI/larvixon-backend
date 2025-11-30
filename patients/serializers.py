from rest_framework import serializers


class PatientSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    pesel = serializers.CharField(max_length=11, allow_null=True, required=False)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    birth_date = serializers.DateField(allow_null=True, required=False)
    gender = serializers.CharField(max_length=50, allow_null=True, required=False)
    phone = serializers.CharField(max_length=20, allow_null=True, required=False)
    email = serializers.EmailField(allow_null=True, required=False)
    address_line = serializers.CharField(
        max_length=255, allow_null=True, required=False
    )
    city = serializers.CharField(max_length=100, allow_null=True, required=False)
    postal_code = serializers.CharField(max_length=20, allow_null=True, required=False)
    country = serializers.CharField(max_length=2, allow_null=True, required=False)
