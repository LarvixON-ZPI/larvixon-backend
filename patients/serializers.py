from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()

    class Meta:
        model = Patient
        fields = [
            "id",
            "pesel",
            "first_name",
            "last_name",
            "birth_date",
            "age",
            "sex",
            "weight_kg",
            "height_cm",
        ]
